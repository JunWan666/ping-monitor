import platform
import re
import statistics
import subprocess
import time
from typing import Dict, Generator, List

from ping3 import ping


class PingService:
    """Ping monitoring service."""

    @staticmethod
    def _build_summary(packet_sent: int, packet_received: int, results: List[float]) -> Dict:
        valid_results = [float(delay) for delay in results if delay is not None]
        packet_loss = ((packet_sent - packet_received) / packet_sent * 100) if packet_sent > 0 else 100.0

        if valid_results:
            min_rtt = min(valid_results)
            max_rtt = max(valid_results)
            avg_rtt = statistics.mean(valid_results)
            status = "success"
        else:
            min_rtt = None
            max_rtt = None
            avg_rtt = None
            status = "unreachable" if packet_received == 0 else "timeout"

        return {
            "packet_sent": packet_sent,
            "packet_received": packet_received,
            "packet_loss": round(packet_loss, 2),
            "min_rtt": round(min_rtt, 2) if min_rtt is not None else None,
            "max_rtt": round(max_rtt, 2) if max_rtt is not None else None,
            "avg_rtt": round(avg_rtt, 2) if avg_rtt is not None else None,
            "status": status,
        }

    @staticmethod
    def ping_host(address: str, count: int = 10, timeout: int = 2) -> Dict:
        results: List[float] = []
        packet_sent = 0
        packet_received = 0

        for _ in range(count):
            packet_sent += 1
            try:
                delay = ping(address, timeout=timeout, unit="ms")
                if delay is not None:
                    packet_received += 1
                    results.append(delay)
            except Exception:
                pass

        return PingService._build_summary(packet_sent, packet_received, results)

    @staticmethod
    def ping_host_stream(address: str, count: int = 10, timeout: int = 2) -> Generator[Dict, None, None]:
        results: List[float] = []
        packet_sent = 0
        packet_received = 0

        yield {
            "type": "start",
            "message": f"开始 Ping {address}，共 {count} 次",
            "address": address,
            "count": count,
        }

        for i in range(count):
            packet_sent += 1
            try:
                delay = ping(address, timeout=timeout, unit="ms")
                if delay is not None:
                    packet_received += 1
                    results.append(delay)
                    yield {
                        "type": "ping",
                        "sequence": i + 1,
                        "total": count,
                        "status": "success",
                        "delay": round(delay, 2),
                        "message": f"来自 {address} 的回复: 时间={round(delay, 2)}ms",
                        "address": address,
                    }
                else:
                    yield {
                        "type": "ping",
                        "sequence": i + 1,
                        "total": count,
                        "status": "timeout",
                        "message": "请求超时",
                        "address": address,
                    }
            except Exception as exc:
                yield {
                    "type": "ping",
                    "sequence": i + 1,
                    "total": count,
                    "status": "error",
                    "message": f"Ping 失败: {exc}",
                    "address": address,
                }

        yield {
            "type": "summary",
            **PingService._build_summary(packet_sent, packet_received, results),
        }

        yield {
            "type": "complete",
            "message": "Ping 测试完成",
        }

    @staticmethod
    def ping_host_native(address: str, count: int = 10) -> Dict:
        system = platform.system()
        cmd = ["ping", "-n" if system == "Windows" else "-c", str(count), address]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=count * 2,
                encoding="utf-8" if system == "Windows" else None,
            )
            output = result.stdout

            if system == "Windows":
                return PingService._parse_windows_ping(output, count)
            return PingService._parse_linux_ping(output, count)
        except Exception as exc:
            return {
                "packet_sent": count,
                "packet_received": 0,
                "packet_loss": 100.0,
                "min_rtt": None,
                "max_rtt": None,
                "avg_rtt": None,
                "status": "error",
                "error": str(exc),
            }

    @staticmethod
    def _parse_windows_ping(output: str, count: int) -> Dict:
        loss_match = re.search(r"丢失 = (\d+)", output)
        packet_lost = int(loss_match.group(1)) if loss_match else count
        packet_received = count - packet_lost
        packet_loss = (packet_lost / count * 100) if count > 0 else 100.0

        rtt_match = re.search(r"最短 = (\d+)ms，最长 = (\d+)ms，平均 = (\d+)ms", output)
        if rtt_match:
            min_rtt = float(rtt_match.group(1))
            max_rtt = float(rtt_match.group(2))
            avg_rtt = float(rtt_match.group(3))
            status = "success"
        else:
            min_rtt = max_rtt = avg_rtt = None
            status = "unreachable" if packet_received == 0 else "timeout"

        return {
            "packet_sent": count,
            "packet_received": packet_received,
            "packet_loss": round(packet_loss, 2),
            "min_rtt": min_rtt,
            "max_rtt": max_rtt,
            "avg_rtt": avg_rtt,
            "status": status,
        }

    @staticmethod
    def _parse_linux_ping(output: str, count: int) -> Dict:
        loss_match = re.search(r"(\d+)% packet loss", output)
        packet_loss = float(loss_match.group(1)) if loss_match else 100.0
        packet_received = int(count * (1 - packet_loss / 100))

        rtt_match = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)", output)
        if rtt_match:
            min_rtt = float(rtt_match.group(1))
            avg_rtt = float(rtt_match.group(2))
            max_rtt = float(rtt_match.group(3))
            status = "success"
        else:
            min_rtt = max_rtt = avg_rtt = None
            status = "unreachable" if packet_received == 0 else "timeout"

        return {
            "packet_sent": count,
            "packet_received": packet_received,
            "packet_loss": packet_loss,
            "min_rtt": min_rtt,
            "max_rtt": max_rtt,
            "avg_rtt": avg_rtt,
            "status": status,
        }
