import platform
import subprocess
import re
from typing import Dict, List, Optional, Generator
from ping3 import ping
import statistics
import time
import asyncio


class PingService:
    """Ping监控服务"""
    
    @staticmethod
    def ping_host(address: str, count: int = 10, timeout: int = 2) -> Dict:
        """
        Ping主机并返回结果
        
        Args:
            address: 主机地址(IP或域名)
            count: 发送包数量
            timeout: 超时时间(秒)
            
        Returns:
            {
                'packet_sent': 10,
                'packet_received': 8,
                'packet_loss': 20.0,
                'min_rtt': 10.5,
                'max_rtt': 50.2,
                'avg_rtt': 25.8,
                'status': 'success' | 'unreachable' | 'timeout'
            }
        """
        results = []
        packet_sent = 0
        packet_received = 0
        
        for _ in range(count):
            packet_sent += 1
            try:
                delay = ping(address, timeout=timeout, unit='ms')
                if delay is not None:
                    packet_received += 1
                    results.append(delay)
            except Exception:
                pass
        
        # 计算丢包率
        packet_loss = ((packet_sent - packet_received) / packet_sent * 100) if packet_sent > 0 else 100.0
        
        # 计算延迟统计
        if results:
            min_rtt = min(results)
            max_rtt = max(results)
            avg_rtt = statistics.mean(results)
            status = 'success'
        else:
            min_rtt = None
            max_rtt = None
            avg_rtt = None
            status = 'unreachable' if packet_received == 0 else 'timeout'
        
        return {
            'packet_sent': packet_sent,
            'packet_received': packet_received,
            'packet_loss': round(packet_loss, 2),
            'min_rtt': round(min_rtt, 2) if min_rtt else None,
            'max_rtt': round(max_rtt, 2) if max_rtt else None,
            'avg_rtt': round(avg_rtt, 2) if avg_rtt else None,
            'status': status
        }
    
    @staticmethod
    def ping_host_stream(address: str, count: int = 10, timeout: int = 2) -> Generator[Dict, None, None]:
        """
        流式Ping主机，逐次返回每个ping的结果（用于实时显示）
        
        Args:
            address: 主机地址(IP或域名)
            count: 发送包数量
            timeout: 超时时间(秒)
            
        Yields:
            每次ping的结果字典
        """
        results = []
        packet_sent = 0
        packet_received = 0
        
        # 发送开始消息
        yield {
            'type': 'start',
            'message': f'开始Ping {address}，共{count}次',
            'address': address,
            'count': count
        }
        
        for i in range(count):
            packet_sent += 1
            try:
                start_time = time.time()
                delay = ping(address, timeout=timeout, unit='ms')
                
                if delay is not None:
                    packet_received += 1
                    results.append(delay)
                    yield {
                        'type': 'ping',
                        'sequence': i + 1,
                        'total': count,
                        'status': 'success',
                        'delay': round(delay, 2),
                        'message': f'来自 {address} 的回复: 时间={round(delay, 2)}ms',
                        'address': address
                    }
                else:
                    yield {
                        'type': 'ping',
                        'sequence': i + 1,
                        'total': count,
                        'status': 'timeout',
                        'message': f'请求超时',
                        'address': address
                    }
            except Exception as e:
                yield {
                    'type': 'ping',
                    'sequence': i + 1,
                    'total': count,
                    'status': 'error',
                    'message': f'Ping失败: {str(e)}',
                    'address': address
                }
        
        # 计算统计信息
        packet_loss = ((packet_sent - packet_received) / packet_sent * 100) if packet_sent > 0 else 100.0
        
        if results:
            min_rtt = min(results)
            max_rtt = max(results)
            avg_rtt = statistics.mean(results)
            status = 'success'
        else:
            min_rtt = None
            max_rtt = None
            avg_rtt = None
            status = 'unreachable' if packet_received == 0 else 'timeout'
        
        # 发送汇总消息(不包含文本,只有数据)
        summary = {
            'type': 'summary',
            'packet_sent': packet_sent,
            'packet_received': packet_received,
            'packet_loss': round(packet_loss, 2),
            'min_rtt': round(min_rtt, 2) if min_rtt else None,
            'max_rtt': round(max_rtt, 2) if max_rtt else None,
            'avg_rtt': round(avg_rtt, 2) if avg_rtt else None,
            'status': status
        }
        
        yield summary
        
        # 发送完成消息
        yield {
            'type': 'complete',
            'message': 'Ping测试完成!'
        }
    
    @staticmethod
    def ping_host_native(address: str, count: int = 10) -> Dict:
        """
        使用系统原生ping命令(备用方案，需要管理员权限时使用ping3)
        """
        system = platform.system()
        
        if system == "Windows":
            cmd = ['ping', '-n', str(count), address]
        else:
            cmd = ['ping', '-c', str(count), address]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=count * 2,
                encoding='utf-8' if system == "Windows" else None
            )
            output = result.stdout
            
            # 解析结果
            if system == "Windows":
                return PingService._parse_windows_ping(output, count)
            else:
                return PingService._parse_linux_ping(output, count)
                
        except Exception as e:
            return {
                'packet_sent': count,
                'packet_received': 0,
                'packet_loss': 100.0,
                'min_rtt': None,
                'max_rtt': None,
                'avg_rtt': None,
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def _parse_windows_ping(output: str, count: int) -> Dict:
        """解析Windows ping结果"""
        # 提取丢包率
        loss_match = re.search(r'丢失 = (\d+)', output)
        packet_lost = int(loss_match.group(1)) if loss_match else count
        packet_received = count - packet_lost
        packet_loss = (packet_lost / count * 100) if count > 0 else 100.0
        
        # 提取延迟
        rtt_match = re.search(r'最短 = (\d+)ms，最长 = (\d+)ms，平均 = (\d+)ms', output)
        if rtt_match:
            min_rtt = float(rtt_match.group(1))
            max_rtt = float(rtt_match.group(2))
            avg_rtt = float(rtt_match.group(3))
            status = 'success'
        else:
            min_rtt = max_rtt = avg_rtt = None
            status = 'unreachable' if packet_received == 0 else 'timeout'
        
        return {
            'packet_sent': count,
            'packet_received': packet_received,
            'packet_loss': round(packet_loss, 2),
            'min_rtt': min_rtt,
            'max_rtt': max_rtt,
            'avg_rtt': avg_rtt,
            'status': status
        }
    
    @staticmethod
    def _parse_linux_ping(output: str, count: int) -> Dict:
        """解析Linux ping结果"""
        # 提取丢包率
        loss_match = re.search(r'(\d+)% packet loss', output)
        packet_loss = float(loss_match.group(1)) if loss_match else 100.0
        packet_received = int(count * (1 - packet_loss / 100))
        
        # 提取延迟
        rtt_match = re.search(r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)', output)
        if rtt_match:
            min_rtt = float(rtt_match.group(1))
            avg_rtt = float(rtt_match.group(2))
            max_rtt = float(rtt_match.group(3))
            status = 'success'
        else:
            min_rtt = max_rtt = avg_rtt = None
            status = 'unreachable' if packet_received == 0 else 'timeout'
        
        return {
            'packet_sent': count,
            'packet_received': packet_received,
            'packet_loss': packet_loss,
            'min_rtt': min_rtt,
            'max_rtt': max_rtt,
            'avg_rtt': avg_rtt,
            'status': status
        }
