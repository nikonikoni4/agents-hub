# Systematic Debugging

---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes. Systematic debugging method for complex bugs that resist quick fixes (2-3+ failed attempts). Forces global data flow analysis with multi-agent review to avoid local thinking traps. TRIGGER when (1) same bug fails 2-3+ times, (2) "状态没改变/不工作/没反应" reported repeatedly, (3) about to guess/try random fixes, (4) unsure why code should work.
---

## When to Use This Skill

**MANDATORY trigger conditions** (any one applies):
- Bug persists after 2-3 fix attempts
- User reports "not working / no change / no response" repeatedly
- You're about to guess or try solutions randomly
- Uncertain why the current approach should work
- Cross-component state synchronization issues
- Multi-instance hook or component state problems

**Core problem this solves**: Breaking out of "local thinking loops" where you fixate on one module's logic while missing architectural issues (e.g., state isolation, instance duplication, data flow interruption).

---

## Core Principle

**Never debug in isolation.** Always map the FULL data flow from source to destination before adding a single console.log.

---

## Step 1: Draw Global Data Flow

### 1.1 Identify All Entities

List every component/module/store involved in the feature:

```
[Data Source] → [Middleware/Hooks] → [State Stores] → [Computed Values] → [UI Components]
```

**Example** (React state management):
```
User Action (ChatArea)
  ↓
compressAgent() call
  ↓
useCompressStatusStore.startCompress()  ← [WRITE]
  ↓
pendingAgents Set updated
  ↓
useMembers() in ChatArea reads store    ← [READ instance 1]
  ↓
useMembers() in RightSidebar reads store ← [READ instance 2]
  ↓
membersWithCompressing computed
  ↓
MemberItem renders "compressing: true"
```

### 1.2 Mark Instance Boundaries

**CRITICAL**: Identify where multiple instances exist:
- React hooks called from different components = separate instances
- Class instances created with `new`
- Functions with closure state

**Mark each instance explicitly**:
```
✓ Global store (single instance, shared)
✗ useState in hook (per-caller instance, isolated)
✗ Class with `new` (each instantiation separate)
```

### 1.3 Trace Value Transformations

For each step, note:
- **Type**: Raw value / Computed / Derived
- **Read/Write**: Who reads, who writes
- **Scope**: Global / Module / Local / Closure

---

## Step 2: Multi-Agent Review (Mandatory)

**Purpose**: Catch incorrect assumptions about data flow BEFORE writing logs.

### 2.1 Spawn Review Agents

Create **2-3 independent review agents** with this prompt:

```
Review the data flow diagram for [feature]. Your job is to find errors in the flow:

1. Are there missing steps?
2. Are instances marked correctly (global vs local)?
3. Are there state isolation issues (useState in hooks called multiple times)?
4. Are computed values reading from the right source?
5. Could the flow be interrupted anywhere?

Be skeptical. Challenge every "should work" assumption.
```

### 2.2 Consolidate Findings

Wait for all agents to respond. Look for:
- **Agreement**: Likely correct
- **Disagreement**: Dig deeper, one agent spotted something
- **Common concerns**: High-priority issues

**If any agent raises state isolation / instance duplication concerns**: This is your root cause 80% of the time.

---

## Step 3: Add Strategic Logs

**Only after data flow is validated**, add logs at critical connection points:

### 3.1 Log Placement Rules

```
[Source] → LOG HERE
[State Write] → LOG HERE (before + after)
[State Read] → LOG HERE (show value)
[Computed] → LOG HERE (inputs + output)
[UI Render] → LOG HERE (final props)
```

### 3.2 Log Format

```typescript
console.log('[Module] Action:', data, 'Context:', additionalContext);
```

**Example**:
```typescript
// At write point
console.log('[CompressStore] startCompress:', agentName, 'pendingAgents:', Array.from(next));

// At read point
console.log('[useMembers] pendingAgents from store:', Array.from(pendingAgents));

// At computed point
console.log('[useMembers] membersWithCompressing:', 
  result.map(m => ({ name: m.name, compressing: m.compressing }))
);

// At render point
console.log('[MemberItem]', member.name, 'compressing:', member.compressing);
```

### 3.3 Verify Logs Form Complete Chain

Logs should trace the value from source to destination with NO GAPS:
```
✓ [Source] writes X
✓ [Store] receives X
✓ [Consumer] reads X
✓ [UI] renders X

✗ Missing any step = flow is broken there
```

---

## Step 4: Execute and Analyze

### 4.1 Run the Flow

Execute the user action and observe console logs in order.

### 4.2 Spot the Break

**Expected**: Logs form complete chain source → destination
**Actual**: Look for:
- Missing log (flow stopped)
- Wrong value (transformation error)
- Multiple instances showing different values (isolation issue)

### 4.3 Root Cause Patterns

| Pattern | Root Cause |
|---------|-----------|
| Write logs but no read logs | State not subscribed / wrong store |
| Multiple hooks show different values | Local state instead of global |
| Computed value wrong despite correct input | Stale closure / missing dependency |
| Read logs show correct value but UI wrong | Render optimization / memo issue |

---

## Common Pitfalls to Avoid

1. **Assuming "this should work"** → Draw it out first
2. **Debugging one module in isolation** → Always trace full flow
3. **Skipping multi-agent review** → Your mental model may be wrong
4. **Adding logs randomly** → Target connection points only
5. **Not marking instance boundaries** → Miss isolation issues

---

## Example: State Not Updating in RightSidebar

**Symptom**: User clicks compress, ChatArea shows "compressing...", but RightSidebar member list doesn't update.

### Step 1: Draw Flow

```
ChatArea.handleSlashCommand()
  ↓
compressAgent() [from useMembers() instance 1]
  ↓
compressStatusStore.startCompress() [GLOBAL]
  ↓
pendingAgents Set updated
  ↓
??? [Instance 1 reads store]
  ↓
??? [Instance 2 reads store?]
```

**Gap spotted**: Two components call useMembers() → Two instances!

### Step 2: Multi-Agent Review

Agent 1: "Are ChatArea and RightSidebar using the same store subscription?"
Agent 2: "Does useMembers use local state that would be instance-isolated?"
Agent 3: "If pendingAgents is useState, each hook caller gets its own copy."

**Finding**: useMembers has BOTH local useState AND store subscription → Wrong!

### Step 3: Add Logs

```typescript
// In compressAgent
console.log('[useMembers instance ?] compressAgent START:', agentName);

// In store
console.log('[Store] startCompress, pendingAgents:', Array.from(next));

// In useMembers
console.log('[useMembers] Reading pendingAgents:', Array.from(pendingAgents));
```

### Step 4: Analyze

```
[useMembers instance ?] compressAgent START: agent1  // Instance 1
[Store] startCompress, pendingAgents: ['agent1']     // Global ✓
[useMembers] Reading pendingAgents: ['agent1']       // Instance 1 ✓
[useMembers] Reading pendingAgents: []               // Instance 2 ✗ (stale)
```

**Root cause**: Local state in useMembers wasn't updating for instance 2.
**Fix**: Remove local state, use only global store.

---

## Checklist Before Proposing Fix

- [ ] Global data flow diagram drawn
- [ ] Instance boundaries marked
- [ ] Multi-agent review completed
- [ ] Logs placed at all connection points
- [ ] Logs executed and analyzed
- [ ] Root cause identified (not guessed)
- [ ] Fix addresses architectural issue, not symptoms

---

## Integration with Project Workflow

This skill is invoked automatically by the `systematic-debugging` slash command or when you detect the trigger conditions. Once invoked:

1. Stop current debugging approach
2. Follow this skill's steps sequentially
3. Present data flow diagram to user for confirmation
4. Show log output and analysis
5. Propose fix with architectural explanation
