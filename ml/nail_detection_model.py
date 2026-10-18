"""Shared architecture for optional nail localization."""


def build_nail_detector(pretrained=False):
    from torchvision.models.detection import (
        FasterRCNN_MobileNet_V3_Large_320_FPN_Weights,
        fasterrcnn_mobilenet_v3_large_320_fpn,
    )
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    weights = FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.DEFAULT if pretrained else None
    model = fasterrcnn_mobilenet_v3_large_320_fpn(weights=weights, weights_backbone=None)
    model.roi_heads.box_predictor = FastRCNNPredictor(model.roi_heads.box_predictor.cls_score.in_features, 2)
    return model
