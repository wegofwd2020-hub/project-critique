# mambakkam Lane Configuration Status

## Current State (2026-09-15)

### Hardware
- **Machine**: mambakkam (100.101.249.109)
- **Role**: Primary desktop, aggregator for local_watch
- **Ollama**: v0.33.3 installed
- **Models**: 
  - qwen2.5-coder:7b (4.7 GB) - coding model
  - qwen2.5:7b-instruct-q4_K_M (4.7 GB) - general model

### Current Lane Configuration
- **Role**: Lane A (default Claude)
- **Provider**: Not configured (default Anthropic)
- **Status**: ⚠️ PARTIALLY CONFIGURED

### What We Just Did (2026-09-15)
1. **Installed Ollama**: Downloaded and installed v0.33.3
2. **Pulled models**: qwen2.5-coder:7b + qwen2.5:7b-instruct-q4_K_M
3. **Created lane config**: `~/.config/claude-lane.sh`
4. **Tested Ollama API**: ✅ Working (native + OpenAI-compatible)
5. **Claude Code integration**: ❌ Model recognition issues

### Current Configuration
```bash
# ~/.config/claude-lane.sh
export ANTHROPIC_BASE_URL="http://localhost:11434/v1"
export ANTHROPIC_MODEL="qwen2.5-coder:7b"
export ANTHROPIC_API_KEY="ollama"
```

### Integration Status
- **Ollama API**: ✅ Working perfectly
- **OpenAI-compatible endpoint**: ✅ Tested and functional
- **Claude Code**: ❌ Model recognition blocked
- **Settings file**: Created but not applied

## Target Architecture

### Proposed Role
- **Lane**: Lane A (design/review/memory)
- **Purpose**: Critical thinking, architecture, code review
- **Model**: Local Ollama (qwen2.5-coder:7b)
- **Cost**: $0 after hardware investment

### Required Changes
1. **Fix Claude Code integration**: Resolve model recognition
2. **Test workflow**: Verify design/review tasks work locally
3. **Benchmark**: Compare quality vs Claude API
4. **Configure fallback**: API when local unavailable

### Alternative: Hybrid Approach
- **Primary**: Local Ollama for most work
- **Fallback**: Claude API for critical tasks
- **Decision logic**: Local by default, API for high-stakes work

## Implementation Status

### Completed ✅
- [x] Ollama installed and running
- [x] Coding model pulled (qwen2.5-coder:7b)
- [x] General model available (qwen2.5:7b-instruct-q4_K_M)
- [x] Lane config file created
- [x] Ollama API tested and working
- [x] SSH access via Tailscale

### Pending 🔄
- [ ] Fix Claude Code model recognition
- [ ] Test Claude Code + Ollama integration
- [ ] Apply settings.json model overrides
- [ ] Test design/review workflow
- [ ] Benchmark quality vs Claude API
- [ ] Configure API fallback

### Blocked ⛔
- [ ] Claude Code doesn't recognize Ollama model names
- [ ] Model override settings not being applied
- [ ] Need alternative client or Claude Code update

## Technical Details

### Ollama API Test Results
```bash
# Native API - ✅ Working
curl http://localhost:11434/api/generate
# Returns: Valid responses from qwen2.5-coder:7b

# OpenAI-compatible - ✅ Working  
curl http://localhost:11434/v1/chat/completions
# Returns: Proper OpenAI format responses
```

### Claude Code Issues
```
Error: "qwen2.5-coder:7b" isn't described by this version's model catalog
Tried: modelOverrides in settings.json
Result: Settings not being applied
```

### Settings File Created
```json
{
  "modelOverrides": {
    "qwen2.5-coder:7b": {
      "behavesAs": "claude-fable-5",
      "maxContextTokens": 32768
    }
  }
}
```

## Cost Analysis

### Current (Default Claude)
- **Cost**: Standard Anthropic pricing
- **Quality**: Highest available
- **Pros**: Best performance, no setup
- **Cons**: Ongoing expense

### Target (Local Ollama)
- **Cost**: $0 after hardware
- **Hardware**: Already available
- **Pros**: No ongoing cost, unlimited usage
- **Cons**: Setup complexity, quality unknown

## Next Steps

1. **Immediate**: Decide on Claude Code integration approach
2. **Option A**: Use different client (aider, etc.)
3. **Option B**: Wait for Claude Code update
4. **Option C**: Hybrid with API fallback
5. **Testing**: Validate chosen approach with real work

## Questions to Resolve

1. **Primary question**: Should mambakkam use local Ollama or stay with Claude API?
2. **Integration**: How to make Claude Code work with Ollama models?
3. **Quality**: Is qwen2.5-coder good enough for design/review work?
4. **Fallback**: When to use API vs local?

## Notes

- Ollama installation successful
- Models working perfectly via direct API
- Claude Code integration is the blocker
- Consider alternative clients if Claude Code can't work
- Hybrid approach might be best intermediate step