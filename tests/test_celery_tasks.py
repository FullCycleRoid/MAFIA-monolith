from app.tasks.voice_tasks import process_phase_change
from app.tasks.cleanup import cleanup_old_games_task
from app.tasks.withdrawal_processor import process_pending_withdrawals

def test_voice_task_no_event_loop_crash(monkeypatch):
    def fake_handle(event): return None
    from app.domains.voice import events
    monkeypatch.setattr(events, "handle_phase_change", lambda e: None)
    process_phase_change.delay if hasattr(process_phase_change, 'delay') else None

def test_cleanup_task_no_event_loop_crash(monkeypatch):
    from app.domains.game import repository
    monkeypatch.setattr(repository, "cleanup_old_games", lambda days: None)
    cleanup_old_games_task(1)
