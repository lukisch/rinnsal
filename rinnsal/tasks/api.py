# -*- coding: utf-8 -*-
"""
Rinnsal Task High-Level API
=============================

Convenience-Funktionen fuer schnellen Zugriff ohne explizite Client-Instanz.
Singleton-Pattern mit globaler Default-DB (analog zu memory/api.py).

Verwendung:
    from rinnsal.tasks import api as tasks

    tasks.init(agent_id="opus")
    tasks.add("Feature X implementieren", priority="high")
    tasks.add("Bug fixen", description="Encoding-Problem")

    for t in tasks.list():
        print(f"[{t['id']}] {t['title']} ({t['status']})")

    tasks.done(1)
    tasks.activate(2)

Author: Lukas Geiger
License: MIT
"""
from typing import Optional, List, Dict

from .client import TaskClient

_client: Optional[TaskClient] = None
_default_db = "rinnsal.db"


def init(
    db_path: Optional[str] = None,
    agent_id: str = "default"
) -> TaskClient:
    """Initialisiert die globale Task-Instanz."""
    global _client
    _client = TaskClient(
        db_path=db_path or _default_db,
        agent_id=agent_id
    )
    return _client


def get_client() -> TaskClient:
    """Gibt die globale Client-Instanz zurueck (lazy init)."""
    global _client
    if _client is None:
        _client = TaskClient(db_path=_default_db, agent_id="default")
    return _client


def set_agent(agent_id: str) -> None:
    """Setzt die Agent-ID fuer neue Tasks."""
    client = get_client()
    client.agent_id = agent_id


# === Task Operations ===

def add(title: str, description: str = "", priority: str = "medium",
        tags: str = "") -> Dict:
    """Erstellt einen neuen Task."""
    return get_client().add(title, description=description,
                            priority=priority, tags=tags)


def list(status: Optional[str] = None, priority: Optional[str] = None,
         include_done: bool = False, limit: int = 50) -> List[Dict]:
    """Listet Tasks auf (default: nur offene/aktive)."""
    return get_client().list(status=status, priority=priority,
                             include_done=include_done, limit=limit)


def get(task_id: int) -> Optional[Dict]:
    """Holt einen einzelnen Task."""
    return get_client().get(task_id)


def done(task_id: int) -> bool:
    """Markiert einen Task als erledigt."""
    return get_client().done(task_id)


def activate(task_id: int) -> bool:
    """Setzt einen Task auf 'active'."""
    return get_client().activate(task_id)


def cancel(task_id: int) -> bool:
    """Storniert einen Task."""
    return get_client().cancel(task_id)


def reopen(task_id: int) -> bool:
    """Oeffnet einen erledigten/stornierten Task erneut."""
    return get_client().reopen(task_id)


def update(task_id: int, title: Optional[str] = None,
           description: Optional[str] = None, priority: Optional[str] = None,
           tags: Optional[str] = None) -> bool:
    """Aktualisiert Task-Felder."""
    return get_client().update(task_id, title=title, description=description,
                               priority=priority, tags=tags)


def delete(task_id: int) -> bool:
    """Loescht einen Task permanent."""
    return get_client().delete(task_id)


def count() -> Dict:
    """Zaehlt Tasks nach Status."""
    return get_client().count()


# === Shortcuts ===

def next_task() -> Optional[Dict]:
    """Gibt den naechsten offenen Task mit hoechster Prioritaet zurueck."""
    tasks = get_client().list(status='open', limit=1)
    return tasks[0] if tasks else None


def active_tasks() -> List[Dict]:
    """Gibt alle aktiven Tasks zurueck."""
    return get_client().list(status='active')
