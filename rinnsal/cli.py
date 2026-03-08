# -*- coding: utf-8 -*-
"""
Rinnsal CLI -- Vereinheitlichter Entry Point
==============================================

rinnsal status
rinnsal memory status|fact|note|context|...
rinnsal chain start|list|stop|log|reset|create
rinnsal connect list|test|send
rinnsal pipe "prompt"
rinnsal version

Author: Lukas Geiger
License: MIT
"""
import argparse
import json
import sys
from typing import Optional


def cmd_version(args) -> int:
    from rinnsal import __version__
    print(f"rinnsal {__version__}")
    return 0


def cmd_status(args) -> int:
    """Gesamtstatus: Memory + Chains + Connectors."""
    print("Rinnsal Status")
    print("=" * 40)

    # Memory
    try:
        from rinnsal.memory import api
        if args.db:
            api.init(db_path=args.db)
        s = api.status()
        print(f"  Memory:  {s['facts_count']} Facts, {s['working_count']} Working, {s['lessons_count']} Lessons")
    except Exception as e:
        print(f"  Memory:  nicht verfuegbar ({e})")

    # Tasks
    try:
        from rinnsal.tasks.client import TaskClient
        tc = TaskClient(db_path=args.db or "rinnsal.db")
        c = tc.count()
        print(f"  Tasks:   {c.get('open', 0)} offen, {c.get('active', 0)} aktiv, {c.get('done', 0)} erledigt")
    except Exception as e:
        print(f"  Tasks:   nicht verfuegbar ({e})")

    # Chains
    try:
        from rinnsal.auto.config import list_chains
        chains = list_chains()
        print(f"  Chains:  {len(chains)} definiert ({', '.join(chains[:5])}{'...' if len(chains) > 5 else ''})")
    except Exception:
        print(f"  Chains:  0 definiert")

    # Connectors
    from rinnsal.connectors import list_connectors
    print(f"  Connectors: {', '.join(list_connectors())}")

    return 0


# === Memory Commands ===

def cmd_memory(args) -> int:
    """Delegiert an Memory-Subcommands."""
    from rinnsal.memory.client import MemoryClient

    client = MemoryClient(
        db_path=args.db or "rinnsal.db",
        agent_id=args.agent or "cli"
    )

    subcmd = args.memory_cmd

    if subcmd == "status":
        s = client.get_status()
        print(f"Rinnsal Memory Status")
        print(f"=====================")
        print(f"DB:              {s['db_path']}")
        print(f"Agent:           {s['agent_id']}")
        print(f"Facts:           {s['facts_count']} ({s['confident_facts']} mit confidence >= 0.8)")
        print(f"Working Memory:  {s['working_count']} aktiv")
        print(f"Lessons:         {s['lessons_count']} aktiv")
        print(f"Sessions:        {s['sessions_count']} total")

    elif subcmd == "fact":
        result = client.add_fact(args.category, args.key, args.value,
                                 confidence=getattr(args, 'confidence', 1.0))
        if result.get('merged'):
            print(f"[OK] Fakt gespeichert: {args.key} = {args.value}")
        else:
            print(f"[SKIP] Nicht ueberschrieben: {result.get('reason', 'unknown')}")

    elif subcmd == "facts":
        facts = client.get_facts(
            category=getattr(args, 'category', None),
            min_confidence=getattr(args, 'min_confidence', 0.0)
        )
        if not facts:
            print("Keine Fakten gefunden.")
        elif getattr(args, 'json', False):
            print(json.dumps(facts, indent=2, ensure_ascii=False))
        else:
            print(f"{'Category':<12} {'Key':<20} {'Value':<30} {'Conf':>5}")
            print("-" * 70)
            for f in facts:
                val = f['value'][:28] + ".." if len(f['value']) > 30 else f['value']
                print(f"{f['category']:<12} {f['key']:<20} {val:<30} {f['confidence']:>5.2f}")

    elif subcmd == "note":
        result = client.add_working(content=args.content)
        print(f"[OK] Notiz gespeichert (ID: {result['id']})")

    elif subcmd == "context":
        ctx = client.generate_context()
        print(ctx)

    else:
        print(f"Unbekannter Memory-Befehl: {subcmd}")
        return 1

    return 0


# === Chain Commands ===

def cmd_chain(args) -> int:
    subcmd = args.chain_cmd

    if subcmd == "start":
        from rinnsal.auto.chain import run_chain
        bg = getattr(args, 'background', False)
        return run_chain(args.name, background=bg)

    elif subcmd == "list":
        from rinnsal.auto.config import list_chains
        chains = list_chains()
        if not chains:
            print("Keine Ketten definiert.")
        else:
            for c in chains:
                print(f"  {c}")
        return 0

    elif subcmd == "status":
        from rinnsal.auto.chain import show_status
        return show_status(getattr(args, 'name', None))

    elif subcmd == "stop":
        from rinnsal.auto.chain import stop_chain
        return stop_chain(args.name, reason=getattr(args, 'reason', None))

    elif subcmd == "log":
        from rinnsal.auto.chain import show_log
        return show_log(args.name, lines=getattr(args, 'lines', 20))

    elif subcmd == "reset":
        from rinnsal.auto.chain import reset_chain
        return reset_chain(args.name)

    elif subcmd == "create":
        from rinnsal.auto.chain_creator import create_chain
        create_chain()
        return 0

    else:
        print(f"Unbekannter Chain-Befehl: {subcmd}")
        return 1


# === Connector Commands ===

def cmd_connect(args) -> int:
    subcmd = args.connect_cmd

    if subcmd == "list":
        from rinnsal.connectors import list_connectors
        for c in list_connectors():
            print(f"  {c}")
        return 0

    elif subcmd == "test":
        from rinnsal.connectors import load_connector
        try:
            conn = load_connector(args.type)
            print(f"Teste {args.type}...")
            if conn.connect():
                print(f"[OK] {args.type} verbunden.")
                conn.disconnect()
            else:
                print(f"[FEHLER] {args.type} Verbindung fehlgeschlagen.")
                return 1
        except Exception as e:
            print(f"[FEHLER] {e}")
            return 1
        return 0

    elif subcmd == "send":
        from rinnsal.connectors import load_connector
        try:
            conn = load_connector(args.type)
            conn.connect()
            if conn.send_message(args.recipient, args.message):
                print(f"[OK] Nachricht gesendet via {args.type}.")
            else:
                print(f"[FEHLER] Senden fehlgeschlagen.")
                return 1
        except Exception as e:
            print(f"[FEHLER] {e}")
            return 1
        return 0

    else:
        print(f"Unbekannter Connect-Befehl: {subcmd}")
        return 1


# === Task Commands ===

def cmd_task(args) -> int:
    """Delegiert an Task-Subcommands."""
    from rinnsal.tasks.client import TaskClient

    client = TaskClient(
        db_path=args.db or "rinnsal.db",
        agent_id=args.agent or "cli"
    )

    subcmd = args.task_cmd

    if subcmd == "add":
        result = client.add(
            title=args.title,
            description=getattr(args, 'description', '') or '',
            priority=getattr(args, 'priority', 'medium') or 'medium',
            tags=getattr(args, 'tags', '') or ''
        )
        print(f"[OK] Task #{result['id']} erstellt: {result['title']}")

    elif subcmd == "list":
        status_filter = getattr(args, 'status', None)
        include_done = getattr(args, 'all', False)
        tasks = client.list(status=status_filter, include_done=include_done)
        if not tasks:
            print("Keine Tasks gefunden.")
        elif getattr(args, 'json', False):
            print(json.dumps(tasks, indent=2, ensure_ascii=False))
        else:
            _print_task_table(tasks)

    elif subcmd == "done":
        if client.done(args.id):
            print(f"[OK] Task #{args.id} erledigt.")
        else:
            print(f"[FEHLER] Task #{args.id} nicht gefunden.")
            return 1

    elif subcmd == "activate":
        if client.activate(args.id):
            print(f"[OK] Task #{args.id} aktiviert.")
        else:
            print(f"[FEHLER] Task #{args.id} nicht gefunden.")
            return 1

    elif subcmd == "cancel":
        if client.cancel(args.id):
            print(f"[OK] Task #{args.id} storniert.")
        else:
            print(f"[FEHLER] Task #{args.id} nicht gefunden.")
            return 1

    elif subcmd == "reopen":
        if client.reopen(args.id):
            print(f"[OK] Task #{args.id} wieder geoeffnet.")
        else:
            print(f"[FEHLER] Task #{args.id} nicht gefunden.")
            return 1

    elif subcmd == "delete":
        if client.delete(args.id):
            print(f"[OK] Task #{args.id} geloescht.")
        else:
            print(f"[FEHLER] Task #{args.id} nicht gefunden.")
            return 1

    elif subcmd == "show":
        task = client.get(args.id)
        if not task:
            print(f"[FEHLER] Task #{args.id} nicht gefunden.")
            return 1
        print(f"Task #{task['id']}")
        print(f"  Titel:       {task['title']}")
        print(f"  Status:      {task['status']}")
        print(f"  Prioritaet:  {task['priority']}")
        print(f"  Agent:       {task['agent_id']}")
        if task['description']:
            print(f"  Beschreibung: {task['description']}")
        if task['tags']:
            print(f"  Tags:        {task['tags']}")
        print(f"  Erstellt:    {task['created_at'][:19]}")
        if task['done_at']:
            print(f"  Erledigt:    {task['done_at'][:19]}")

    elif subcmd == "count":
        c = client.count()
        print(f"Tasks: {c['total']} total")
        for s in ('open', 'active', 'done', 'cancelled'):
            if c[s] > 0:
                print(f"  {s:<12} {c[s]}")

    else:
        print(f"Unbekannter Task-Befehl: {subcmd}")
        return 1

    return 0


def _print_task_table(tasks):
    """Gibt eine formatierte Task-Tabelle aus."""
    pri_sym = {'critical': '!!!', 'high': '!!', 'medium': '!', 'low': '.'}
    stat_sym = {'open': ' ', 'active': '>', 'done': 'x', 'cancelled': '-'}
    print(f"{'ID':>4}  {'S':1}  {'Pri':3}  {'Titel':<50}  {'Agent':<10}")
    print("-" * 75)
    for t in tasks:
        s = stat_sym.get(t['status'], '?')
        p = pri_sym.get(t['priority'], '?')
        title = t['title'][:48] + ".." if len(t['title']) > 50 else t['title']
        print(f"{t['id']:>4}  {s:1}  {p:<3}  {title:<50}  {t['agent_id']:<10}")


# === Pipe Command ===

def cmd_pipe(args) -> int:
    from rinnsal.auto.runner import ClaudeRunner
    runner = ClaudeRunner(
        model=getattr(args, 'model', None) or "claude-sonnet-4-6",
    )
    try:
        output = runner.pipe(args.prompt)
        print(output)
        return 0
    except RuntimeError as e:
        print(f"[FEHLER] {e}", file=sys.stderr)
        return 1


def main(argv: Optional[list] = None) -> int:
    """CLI Entry Point."""
    parser = argparse.ArgumentParser(
        prog='rinnsal',
        description='Rinnsal -- Lightweight LLM Agent Infrastructure'
    )
    parser.add_argument('--db', help='Pfad zur Memory-DB')
    parser.add_argument('--agent', help='Agent-ID')

    subparsers = parser.add_subparsers(dest='command')

    # version
    p_ver = subparsers.add_parser('version', help='Zeigt Version')
    p_ver.set_defaults(func=cmd_version)

    # status
    p_status = subparsers.add_parser('status', help='Gesamtstatus')
    p_status.set_defaults(func=cmd_status)

    # memory
    p_mem = subparsers.add_parser('memory', help='Memory-Befehle')
    mem_sub = p_mem.add_subparsers(dest='memory_cmd')

    mem_sub.add_parser('status', help='Memory-Status')

    p_mf = mem_sub.add_parser('fact', help='Fakt speichern')
    p_mf.add_argument('category', choices=['user', 'project', 'system', 'domain'])
    p_mf.add_argument('key')
    p_mf.add_argument('value')
    p_mf.add_argument('--confidence', '-c', type=float, default=1.0)

    p_mfs = mem_sub.add_parser('facts', help='Fakten auflisten')
    p_mfs.add_argument('--category', '-c', choices=['user', 'project', 'system', 'domain'])
    p_mfs.add_argument('--min-confidence', '-m', type=float, default=0.0)
    p_mfs.add_argument('--json', '-j', action='store_true')

    p_mn = mem_sub.add_parser('note', help='Notiz speichern')
    p_mn.add_argument('content')

    mem_sub.add_parser('context', help='LLM-Kontext generieren')

    p_mem.set_defaults(func=cmd_memory)

    # chain
    p_chain = subparsers.add_parser('chain', help='Chain-Befehle')
    chain_sub = p_chain.add_subparsers(dest='chain_cmd')

    p_cs = chain_sub.add_parser('start', help='Kette starten')
    p_cs.add_argument('name')
    p_cs.add_argument('--background', '-b', action='store_true')

    chain_sub.add_parser('list', help='Ketten auflisten')

    p_cst = chain_sub.add_parser('status', help='Ketten-Status')
    p_cst.add_argument('name', nargs='?')

    p_cstop = chain_sub.add_parser('stop', help='Kette stoppen')
    p_cstop.add_argument('name')
    p_cstop.add_argument('--reason', '-r')

    p_cl = chain_sub.add_parser('log', help='Ketten-Log')
    p_cl.add_argument('name')
    p_cl.add_argument('--lines', '-n', type=int, default=20)

    p_cr = chain_sub.add_parser('reset', help='Kette zuruecksetzen')
    p_cr.add_argument('name')

    chain_sub.add_parser('create', help='Neue Kette erstellen')

    p_chain.set_defaults(func=cmd_chain)

    # task
    p_task = subparsers.add_parser('task', help='Task-Befehle')
    task_sub = p_task.add_subparsers(dest='task_cmd')

    p_ta = task_sub.add_parser('add', help='Task erstellen')
    p_ta.add_argument('title')
    p_ta.add_argument('--description', '-d', default='')
    p_ta.add_argument('--priority', '-p', choices=['critical', 'high', 'medium', 'low'], default='medium')
    p_ta.add_argument('--tags', '-t', default='')

    p_tl = task_sub.add_parser('list', help='Tasks auflisten')
    p_tl.add_argument('--status', '-s', choices=['open', 'active', 'done', 'cancelled'])
    p_tl.add_argument('--all', '-a', action='store_true', help='Auch erledigte/stornierte')
    p_tl.add_argument('--json', '-j', action='store_true')

    p_ts = task_sub.add_parser('show', help='Task-Details')
    p_ts.add_argument('id', type=int)

    p_td = task_sub.add_parser('done', help='Task erledigen')
    p_td.add_argument('id', type=int)

    p_tact = task_sub.add_parser('activate', help='Task aktivieren')
    p_tact.add_argument('id', type=int)

    p_tc = task_sub.add_parser('cancel', help='Task stornieren')
    p_tc.add_argument('id', type=int)

    p_tr = task_sub.add_parser('reopen', help='Task wieder oeffnen')
    p_tr.add_argument('id', type=int)

    p_tdel = task_sub.add_parser('delete', help='Task loeschen')
    p_tdel.add_argument('id', type=int)

    task_sub.add_parser('count', help='Task-Zaehler')

    p_task.set_defaults(func=cmd_task)

    # connect
    p_conn = subparsers.add_parser('connect', help='Connector-Befehle')
    conn_sub = p_conn.add_subparsers(dest='connect_cmd')

    conn_sub.add_parser('list', help='Connectors auflisten')

    p_ct = conn_sub.add_parser('test', help='Connector testen')
    p_ct.add_argument('type', choices=['telegram', 'discord', 'homeassistant'])

    p_csend = conn_sub.add_parser('send', help='Nachricht senden')
    p_csend.add_argument('type', choices=['telegram', 'discord', 'homeassistant'])
    p_csend.add_argument('recipient')
    p_csend.add_argument('message')

    p_conn.set_defaults(func=cmd_connect)

    # pipe
    p_pipe = subparsers.add_parser('pipe', help='Einzelner LLM-Aufruf')
    p_pipe.add_argument('prompt')
    p_pipe.add_argument('--model', '-m')
    p_pipe.set_defaults(func=cmd_pipe)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
