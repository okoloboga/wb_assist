#!/usr/bin/env python3
"""
Redis Sentinel мониторинг и health check
"""
import redis
import redis.sentinel
import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class RedisSentinelMonitor:
    """Мониторинг состояния Redis Sentinel"""
    
    def __init__(self):
        self.sentinel_hosts = self._parse_sentinel_hosts()
        self.master_name = os.getenv("REDIS_SENTINEL_MASTER_NAME", "mymaster")
        self.sentinel = None
        self.master = None
        self.replica = None
        
    def _parse_sentinel_hosts(self) -> List[tuple]:
        """Парсинг списка Sentinel хостов"""
        sentinel_hosts = os.getenv("REDIS_SENTINEL_HOSTS", "localhost:26379")
        hosts = []
        
        for host_port in sentinel_hosts.split(','):
            host, port = host_port.strip().split(':')
            hosts.append((host, int(port)))
        
        return hosts
    
    def connect(self) -> bool:
        """Подключение к Redis Sentinel"""
        try:
            self.sentinel = redis.sentinel.Sentinel(self.sentinel_hosts)
            
            # Получаем master и replica
            self.master = self.sentinel.master_for(
                self.master_name,
                socket_timeout=5,
                password=None
            )
            
            self.replica = self.sentinel.slave_for(
                self.master_name,
                socket_timeout=5,
                password=None
            )
            
            logger.info("✅ Подключение к Redis Sentinel успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Redis Sentinel: {e}")
            return False
    
    def check_master_health(self) -> Dict[str, Any]:
        """Проверка здоровья master"""
        try:
            if not self.master:
                return {"status": "error", "message": "Master не подключен"}
            
            # Проверяем ping
            start_time = time.time()
            pong = self.master.ping()
            response_time = (time.time() - start_time) * 1000
            
            if pong:
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"status": "unhealthy", "message": "Master не отвечает на ping"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_replica_health(self) -> Dict[str, Any]:
        """Проверка здоровья replica"""
        try:
            if not self.replica:
                return {"status": "error", "message": "Replica не подключена"}
            
            # Проверяем ping
            start_time = time.time()
            pong = self.replica.ping()
            response_time = (time.time() - start_time) * 1000
            
            if pong:
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"status": "unhealthy", "message": "Replica не отвечает на ping"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_sentinel_health(self) -> Dict[str, Any]:
        """Проверка здоровья Sentinel"""
        try:
            if not self.sentinel:
                return {"status": "error", "message": "Sentinel не подключен"}
            
            # Получаем информацию о master
            master_info = self.sentinel.master(self.master_name)
            
            return {
                "status": "healthy",
                "master_info": master_info,
                "timestamp": datetime.now().isoformat()
            }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_full_status(self) -> Dict[str, Any]:
        """Получение полного статуса Redis Sentinel"""
        if not self.connect():
            return {"status": "error", "message": "Не удалось подключиться к Redis Sentinel"}
        
        master_health = self.check_master_health()
        replica_health = self.check_replica_health()
        sentinel_health = self.check_sentinel_health()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "master": master_health,
            "replica": replica_health,
            "sentinel": sentinel_health,
            "overall_status": "healthy" if all(
                h.get("status") == "healthy" 
                for h in [master_health, replica_health, sentinel_health]
            ) else "unhealthy"
        }
    
    def monitor_loop(self, interval: int = 30):
        """Цикл мониторинга"""
        logger.info(f"🔄 Запуск мониторинга Redis Sentinel каждые {interval} секунд")
        
        while True:
            try:
                status = self.get_full_status()
                
                if status["overall_status"] == "healthy":
                    logger.info("✅ Redis Sentinel: Все сервисы работают нормально")
                else:
                    logger.warning("⚠️ Redis Sentinel: Обнаружены проблемы")
                    logger.warning(f"   Master: {status['master']}")
                    logger.warning(f"   Replica: {status['replica']}")
                    logger.warning(f"   Sentinel: {status['sentinel']}")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Мониторинг остановлен пользователем")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                time.sleep(interval)

def main():
    """Главная функция"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    monitor = RedisSentinelMonitor()
    
    # Проверяем подключение
    if not monitor.connect():
        logger.error("Не удалось подключиться к Redis Sentinel")
        return 1
    
    # Получаем статус
    status = monitor.get_full_status()
    print(f"Redis Sentinel Status: {status}")
    
    # Запускаем мониторинг
    monitor.monitor_loop(interval=30)
    
    return 0

if __name__ == "__main__":
    exit(main())
