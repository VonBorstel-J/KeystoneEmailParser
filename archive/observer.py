# src/utils/observer.py

from typing import Callable, Dict, Any, List, Tuple
import asyncio
import threading
import queue
import time
import logging

logger = logging.getLogger("Observer")
logger.setLevel(logging.DEBUG)


class Observer:
    def __init__(self):
        self._subscribers: List[Tuple[int, Callable[[Dict[str, Any]], Any]]] = []
        self._lock = threading.Lock()
        self._notification_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any], priority: int = 0) -> None:
        """Subscribes a callback to be notified on updates with a given priority."""
        with self._lock:
            self._subscribers.append((priority, callback))
            self._subscribers.sort(key=lambda x: x[0], reverse=True)  # Higher priority first
        logger.debug(f"Subscriber {callback.__name__} added with priority {priority}.")

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        """Unsubscribes a callback from notifications."""
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s[1] != callback]
        logger.debug(f"Subscriber {callback.__name__} removed.")

    def notify(self, config: Dict[str, Any], async_notify: bool = False) -> None:
        """Queues a notification for all subscribers."""
        self._notification_queue.put((config, async_notify))
        logger.debug("Notification queued.")

    def _process_queue(self):
        """Processes the notification queue."""
        while True:
            config, async_notify = self._notification_queue.get()
            if async_notify:
                asyncio.run(self._async_notify(config))
            else:
                self._batch_notify(config)
            self._notification_queue.task_done()

    def _batch_notify(self, config: Dict[str, Any]):
        """Notifies subscribers in batches."""
        with self._lock:
            subscribers = [callback for _, callback in self._subscribers]

        for callback in subscribers:
            try:
                callback(config)
                logger.debug(f"Subscriber {callback.__name__} notified synchronously.")
            except Exception as e:
                logger.error(f"Error notifying subscriber {callback.__name__}: {e}", exc_info=True)

    async def _async_notify(self, config: Dict[str, Any]):
        """Asynchronously notifies subscribers."""
        with self._lock:
            subscribers = [callback for _, callback in self._subscribers]

        tasks = []
        for callback in subscribers:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(callback(config))
            else:
                tasks.append(asyncio.to_thread(callback, config))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for callback, result in zip(subscribers, results):
            if isinstance(result, Exception):
                logger.error(f"Error notifying subscriber {callback.__name__}: {result}", exc_info=True)
            else:
                logger.debug(f"Subscriber {callback.__name__} notified asynchronously.")

    def _retry_notification(self, callback: Callable[[Dict[str, Any]], Any], config: Dict[str, Any], retries: int = 3, delay: float = 1.0):
        """Retries notifying a subscriber upon failure."""
        for attempt in range(1, retries + 1):
            try:
                callback(config)
                logger.debug(f"Subscriber {callback.__name__} notified successfully on attempt {attempt}.")
                break
            except Exception as e:
                logger.error(f"Attempt {attempt}: Error notifying subscriber {callback.__name__}: {e}", exc_info=True)
                time.sleep(delay * attempt)
        else:
            logger.error(f"Failed to notify subscriber {callback.__name__} after {retries} attempts.")

    def add_dynamic_priority(self, callback: Callable[[Dict[str, Any]], Any], new_priority: int) -> None:
        """Dynamically adjusts the priority of a subscriber."""
        with self._lock:
            self._subscribers = [
                (new_priority if cb == callback else prio, cb)
                for prio, cb in self._subscribers
            ]
            self._subscribers.sort(key=lambda x: x[0], reverse=True)
        logger.debug(f"Priority of subscriber {callback.__name__} updated to {new_priority}.")

    def priority_inheritance(self, callback: Callable[[Dict[str, Any]], Any], inherited_priority: int) -> None:
        """Implements priority inheritance for a subscriber."""
        self.add_dynamic_priority(callback, inherited_priority)
        logger.debug(f"Priority inheritance applied to subscriber {callback.__name__} with priority {inherited_priority}.")

    def priority_override(self, callback: Callable[[Dict[str, Any]], Any], override_priority: int) -> None:
        """Overrides the priority of a subscriber."""
        self.add_dynamic_priority(callback, override_priority)
        logger.debug(f"Priority override applied to subscriber {callback.__name__} with priority {override_priority}.")

    def validate_priorities(self) -> bool:
        """Validates the priorities of all subscribers."""
        with self._lock:
            for prio, cb in self._subscribers:
                if not isinstance(prio, int):
                    logger.error(f"Invalid priority {prio} for subscriber {cb.__name__}.")
                    return False
        logger.debug("All subscriber priorities are valid.")
        return True
