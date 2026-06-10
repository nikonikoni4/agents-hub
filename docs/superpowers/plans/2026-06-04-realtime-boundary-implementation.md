# Realtime Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move WebSocket connection management into an independent realtime module and let MCP tools broadcast refresh signals after group chat writes.

**Architecture:** `agents_hub/realtime` owns room connections, refresh event creation, and broadcast helpers. API WebSocket endpoint and HTTP broadcast route depend on realtime; MCP depends on realtime after successful `report_progress` and `complete_task`. Core remains independent of realtime.

**Tech Stack:** Python, FastAPI WebSocket, Pydantic schemas, pytest, pytest-asyncio.

---

### Task 1: Add Realtime Module Tests

**Files:**
- Create: `tests/realtime/test_manager.py`
- Create: `tests/realtime/test_dependencies.py`
- Create: `tests/realtime/test_events.py`
- Create: `tests/realtime/test_boundary.py`

- [ ] Write failing tests that import `agents_hub.realtime.manager.WebSocketManager`, singleton helpers, refresh event helper, and assert realtime modules do not import `agents_hub.api` or `agents_hub.mcp`.
- [ ] Run: `pytest tests/realtime -q`
- [ ] Expected: FAIL because `agents_hub.realtime` does not exist yet.

### Task 2: Implement Realtime Module

**Files:**
- Create: `agents_hub/realtime/__init__.py`
- Create: `agents_hub/realtime/manager.py`
- Create: `agents_hub/realtime/dependencies.py`
- Create: `agents_hub/realtime/events.py`
- Create: `agents_hub/realtime/exceptions.py`

- [ ] Move current WebSocket manager behavior into realtime.
- [ ] Add a refresh event model/helper that serializes to the existing `{type, group_chat_id, timestamp}` shape.
- [ ] Add broadcast helper for group chat refresh.
- [ ] Run: `pytest tests/realtime -q`
- [ ] Expected: PASS.

### Task 3: Rewire API To Realtime

**Files:**
- Modify: `agents_hub/api/websocket/dependencies.py`
- Modify: `agents_hub/api/websocket/endpoint.py`
- Modify: `agents_hub/api/routes/websocket.py`
- Modify: existing WebSocket tests imports as needed.

- [ ] Update API code to import manager/dependencies from realtime.
- [ ] Keep endpoint and HTTP route paths unchanged.
- [ ] Run: `pytest tests/api/test_websocket_manager.py tests/api/test_websocket_dependencies.py tests/api/test_websocket_endpoint.py tests/api/test_websocket_api.py tests/api/test_websocket_boundary.py tests/integration/test_websocket_e2e.py -q`
- [ ] Expected: PASS.

### Task 4: Add MCP Refresh Broadcast Tests

**Files:**
- Modify: `tests/mcp/test_server.py`

- [ ] Add failing tests that patch MCP server's refresh broadcaster and verify `report_progress` and `complete_task` call it after successful group chat writes.
- [ ] Run the two new tests.
- [ ] Expected: FAIL because MCP does not broadcast refresh yet.

### Task 5: Implement MCP Refresh Broadcast

**Files:**
- Modify: `agents_hub/mcp/server.py`

- [ ] Import realtime refresh broadcaster.
- [ ] After successful `report_progress` group chat write, broadcast refresh.
- [ ] After successful `complete_task` group chat write, broadcast refresh.
- [ ] Run MCP tests for speak/finish behavior.
- [ ] Expected: PASS.

### Task 6: Verification

**Files:**
- All touched code and tests.

- [ ] Run targeted realtime/API/MCP tests.
- [ ] Run lint/type checks if configured in pyproject.
- [ ] Run `git diff --check`.
- [ ] Review imports to confirm realtime does not depend on API/MCP and core does not depend on realtime.
