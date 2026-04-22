from __future__ import annotations

from typing import Optional


ONLINE_PACKET_LOSS_THRESHOLD = 100.0

STATUS_UNKNOWN = "unknown"
STATUS_NORMAL = "normal"
STATUS_WARNING = "warning"
STATUS_OFFLINE = "offline"

STATUS_LABELS = {
    STATUS_UNKNOWN: "未知",
    STATUS_NORMAL: "正常",
    STATUS_WARNING: "异常",
    STATUS_OFFLINE: "离线",
}


def normalize_packet_loss(packet_loss: Optional[float]) -> Optional[float]:
    if packet_loss is None:
        return None
    return float(packet_loss)


def is_host_reachable(packet_loss: Optional[float]) -> bool:
    value = normalize_packet_loss(packet_loss)
    return value is not None and value < ONLINE_PACKET_LOSS_THRESHOLD


def is_host_offline(packet_loss: Optional[float]) -> bool:
    value = normalize_packet_loss(packet_loss)
    return value is not None and value >= ONLINE_PACKET_LOSS_THRESHOLD


def is_host_alerting(packet_loss: Optional[float], alert_threshold: Optional[float]) -> bool:
    value = normalize_packet_loss(packet_loss)
    if value is None or value >= ONLINE_PACKET_LOSS_THRESHOLD:
        return False
    threshold = float(alert_threshold if alert_threshold is not None else ONLINE_PACKET_LOSS_THRESHOLD)
    return value >= threshold


def get_host_status_type(packet_loss: Optional[float], alert_threshold: Optional[float]) -> str:
    value = normalize_packet_loss(packet_loss)
    if value is None:
        return STATUS_UNKNOWN
    if value >= ONLINE_PACKET_LOSS_THRESHOLD:
        return STATUS_OFFLINE
    if is_host_alerting(value, alert_threshold):
        return STATUS_WARNING
    return STATUS_NORMAL


def get_host_status_label(packet_loss: Optional[float], alert_threshold: Optional[float]) -> str:
    return STATUS_LABELS[get_host_status_type(packet_loss, alert_threshold)]
