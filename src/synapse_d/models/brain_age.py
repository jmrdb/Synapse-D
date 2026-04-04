"""Brain Age prediction module using SFCN (Simple Fully Convolutional Network).

Predicts biological brain age from T1-weighted MRI volumes.
The Brain Age Gap (predicted age - chronological age) serves as a
biomarker for brain health and neurodegeneration risk.

Model: SFCN pretrained on UK Biobank (12,000+ subjects)
License: MIT
Reference: Peng et al., "Accurate brain age prediction with lightweight
           deep neural networks", Medical Image Analysis, 2021.

Usage:
    from synapse_d.models.brain_age import BrainAgePredictor
    predictor = BrainAgePredictor()
    result = predictor.predict(brain_path=Path("sub-01_T1w_brain.nii.gz"))
"""

from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger

from synapse_d.config import settings

# SFCN model weights path
_WEIGHTS_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "vendor"
    / "layer4-ai-prediction"
    / "SFCN-BrainAge"
    / "brain_age"
    / "run_20190719_00_epoch_best_mae.p"
)

# SFCN expects input size 160x192x160 (after cropping from 182x218x182 MNI)
_INPUT_SHAPE = (160, 192, 160)

# Age range: 42 bins covering ages 14-95 (bin width ~2 years)
_AGE_RANGE = (14, 95)


@dataclass
class BrainAgeResult:
    """Brain age prediction result.

    Attributes:
        predicted_age: Predicted biological brain age in years.
        confidence: Prediction confidence (softmax entropy-based).
        age_distribution: Full probability distribution over age bins.
        brain_age_gap: predicted_age - chronological_age (if provided).
    """

    predicted_age: float
    confidence: float
    age_distribution: list[float]
    brain_age_gap: float | None = None


class SFCN(nn.Module):
    """Simple Fully Convolutional Network for 3D brain MRI.

    Reimplemented from Peng et al. (MIT license).
    Architecture: 6 conv blocks with BN + MaxPool + ReLU, followed by
    average pooling and 1x1 conv classifier.
    """

    def __init__(
        self,
        channel_number: list[int] | None = None,
        output_dim: int = 40,
        dropout: bool = True,
    ):
        super().__init__()
        if channel_number is None:
            channel_number = [32, 64, 128, 256, 256, 64]

        n_layer = len(channel_number)
        self.feature_extractor = nn.Sequential()
        for i in range(n_layer):
            in_ch = 1 if i == 0 else channel_number[i - 1]
            out_ch = channel_number[i]
            if i < n_layer - 1:
                self.feature_extractor.add_module(
                    f"conv_{i}",
                    self._conv_block(in_ch, out_ch, maxpool=True, kernel_size=3, padding=1),
                )
            else:
                self.feature_extractor.add_module(
                    f"conv_{i}",
                    self._conv_block(in_ch, out_ch, maxpool=False, kernel_size=1, padding=0),
                )

        self.classifier = nn.Sequential()
        self.classifier.add_module("average_pool", nn.AvgPool3d([5, 6, 5]))
        if dropout:
            self.classifier.add_module("dropout", nn.Dropout(0.5))
        self.classifier.add_module(
            f"conv_{n_layer}",
            nn.Conv3d(channel_number[-1], output_dim, padding=0, kernel_size=1),
        )

    @staticmethod
    def _conv_block(
        in_ch: int, out_ch: int, maxpool: bool = True, kernel_size: int = 3, padding: int = 0
    ) -> nn.Sequential:
        layers = [
            nn.Conv3d(in_ch, out_ch, padding=padding, kernel_size=kernel_size),
            nn.BatchNorm3d(out_ch),
        ]
        if maxpool:
            layers.append(nn.MaxPool3d(2, stride=2))
        layers.append(nn.ReLU())
        return nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.feature_extractor(x)
        x = self.classifier(x)
        x = F.log_softmax(x, dim=1)
        return x


class BrainAgePredictor:
    """Predict brain age from skull-stripped T1w MRI.

    Args:
        weights_path: Path to pretrained SFCN weights (.p file).
        device: Compute device ('cpu' or 'cuda').
    """

    def __init__(
        self,
        weights_path: Path | None = None,
        device: str | None = None,
    ):
        self.device = device or settings.device
        self.weights_path = weights_path or _WEIGHTS_PATH
        self.model = self._load_model()

    def _load_model(self) -> SFCN:
        """Load SFCN model with pretrained weights.

        The original SFCN checkpoint uses 'module.' prefix (saved with DataParallel).
        We strip this prefix and load with strict=True to ensure all 44 parameters
        match exactly — any mismatch will raise an error rather than silently
        using random weights.
        """
        model = SFCN(output_dim=40, dropout=True)

        if self.weights_path.exists():
            state_dict = torch.load(
                str(self.weights_path),
                map_location=self.device,
                weights_only=False,
            )
            # Handle checkpoint wrapper format
            if isinstance(state_dict, dict) and "model" in state_dict:
                state_dict = state_dict["model"]
            # Strip 'module.' prefix from DataParallel-saved weights
            state_dict = {
                k.removeprefix("module."): v for k, v in state_dict.items()
            }
            model.load_state_dict(state_dict, strict=True)
            loaded = len(state_dict)
            expected = len(model.state_dict())
            logger.info(f"Loaded SFCN weights: {loaded}/{expected} params "
                        f"from {self.weights_path.name}")
        else:
            raise FileNotFoundError(
                f"SFCN weights not found at {self.weights_path}. "
                "Cannot predict Brain Age without pretrained model."
            )

        model.to(self.device)
        model.eval()
        return model

    def predict(
        self, brain_path: Path, chronological_age: float | None = None
    ) -> BrainAgeResult:
        """Predict brain age from a skull-stripped T1w MRI.

        Args:
            brain_path: Path to skull-stripped T1w NIfTI file.
            chronological_age: Actual age (if known) to compute Brain Age Gap.

        Returns:
            BrainAgeResult with predicted age, confidence, and distribution.
        """
        logger.info(f"Predicting brain age for: {brain_path.name}")

        # Load and preprocess
        tensor = self._preprocess(brain_path)

        # Inference
        with torch.no_grad():
            log_probs = self.model(tensor)
            probs = torch.exp(log_probs).squeeze()

        # Convert probability distribution to age
        predicted_age, confidence, distribution = self._probs_to_age(probs)

        # Compute Brain Age Gap if chronological age provided
        gap = None
        if chronological_age is not None:
            gap = predicted_age - chronological_age

        result = BrainAgeResult(
            predicted_age=predicted_age,
            confidence=confidence,
            age_distribution=distribution,
            brain_age_gap=gap,
        )

        logger.info(f"Predicted brain age: {predicted_age:.1f} years "
                    f"(confidence: {confidence:.2f})")
        if gap is not None:
            logger.info(f"Brain Age Gap: {gap:+.1f} years")

        return result

    def _preprocess(self, brain_path: Path) -> torch.Tensor:
        """Load and preprocess MRI for SFCN input.

        Performs: load → normalize → center-crop to 160x192x160 → add batch/channel dims.

        Args:
            brain_path: Path to skull-stripped T1w NIfTI.

        Returns:
            Preprocessed tensor of shape (1, 1, 160, 192, 160).
        """
        img = nib.load(str(brain_path))
        data = np.asanyarray(img.dataobj, dtype=np.float32)

        # Intensity normalization (z-score on non-zero voxels)
        mask = data > 0
        if mask.sum() > 0:
            data[mask] = (data[mask] - data[mask].mean()) / (data[mask].std() + 1e-8)

        # Center crop to expected input shape
        data = self._center_crop(data, _INPUT_SHAPE)

        # To tensor: (1, 1, D, H, W)
        tensor = torch.from_numpy(data).unsqueeze(0).unsqueeze(0)
        return tensor.to(self.device)

    @staticmethod
    def _center_crop(data: np.ndarray, target_shape: tuple[int, ...]) -> np.ndarray:
        """Center-crop or pad a 3D volume to target shape.

        Args:
            data: Input 3D array.
            target_shape: Desired (D, H, W).

        Returns:
            Cropped/padded array of target_shape.
        """
        result = np.zeros(target_shape, dtype=data.dtype)
        starts_src = []
        starts_tgt = []
        sizes = []
        for i in range(3):
            src_s = data.shape[i]
            tgt_s = target_shape[i]
            if src_s >= tgt_s:
                starts_src.append((src_s - tgt_s) // 2)
                starts_tgt.append(0)
                sizes.append(tgt_s)
            else:
                starts_src.append(0)
                starts_tgt.append((tgt_s - src_s) // 2)
                sizes.append(src_s)

        result[
            starts_tgt[0]: starts_tgt[0] + sizes[0],
            starts_tgt[1]: starts_tgt[1] + sizes[1],
            starts_tgt[2]: starts_tgt[2] + sizes[2],
        ] = data[
            starts_src[0]: starts_src[0] + sizes[0],
            starts_src[1]: starts_src[1] + sizes[1],
            starts_src[2]: starts_src[2] + sizes[2],
        ]
        return result

    @staticmethod
    def _probs_to_age(probs: torch.Tensor) -> tuple[float, float, list[float]]:
        """Convert age bin probabilities to predicted age.

        Args:
            probs: Softmax probabilities over age bins (40 bins).

        Returns:
            Tuple of (predicted_age, confidence, distribution_list).
        """
        probs_np = probs.cpu().numpy().flatten()
        n_bins = len(probs_np)

        # Bin centers: linearly spaced between age range
        bin_centers = np.linspace(_AGE_RANGE[0], _AGE_RANGE[1], n_bins)

        # Expected value = weighted sum
        predicted_age = float(np.sum(bin_centers * probs_np))

        # Confidence: 1 - normalized entropy
        entropy = -np.sum(probs_np * np.log(probs_np + 1e-10))
        max_entropy = np.log(n_bins)
        confidence = float(1.0 - entropy / max_entropy)

        return predicted_age, confidence, probs_np.tolist()
