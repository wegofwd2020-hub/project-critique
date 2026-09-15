# vaganam Lane Configuration Status

## Current State (2026-09-15)

### Hardware
- **Machine**: vaganam (100.68.237.79)
- **GPU**: NVIDIA GPU with CUDA 13.0
- **RAM**: 62GB total, 41GB available
- **Ollama**: v0.33.2 installed
- **Models**: llama3:latest (4.7 GB)

### Current Lane Configuration
- **Role**: Lane B (cheap draft box)
- **Provider**: OpenRouter
- **Model**: z-ai/glm-4.6
- **Config File**: `~/.config/claude-lane.sh`
- **Status**: ✅ LIVE and WORKING

### Current Configuration
```bash
# ~/.config/claude-lane.sh
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_MODEL="z-ai/glm-4.6"
export ANTHROPIC_SMALL_FAST_MODEL="z-ai/glm-4.7-flash"
```

### Integration
- **bashrc**: Sources claude-lane.sh automatically
- **OpenRouter Key**: `~/.secrets/openrouter.env` synced via Syncthing
- **Cost**: ~$0.75/1M tokens
- **Balance**: $0.21 remaining (as of 2026-09-15)

## Target Architecture

### Proposed Role
- **Lane**: Lane B (cheap draft box)
- **Purpose**: Bulk coding work, synthetic-only tasks, high-volume operations
- **Model**: Local Ollama (qwen2.5-coder:7b or similar)
- **Cost**: $0 after hardware investment

### Required Changes
1. **Pull coding model**: `ollama pull qwen2.5-coder:7b`
2. **Update lane config**: Switch from OpenRouter to local Ollama
3. **Test integration**: Verify Claude Code works with local model
4. **Benchmark**: Compare performance vs OpenRouter

### Alternative: Hybrid Approach
- **Primary**: Local Ollama for bulk work
- **Fallback**: OpenRouter when local model unavailable
- **Decision logic**: Use local by default, fallback to API on errors

## Implementation Status

### Completed ✅
- [x] Ollama installed
- [x] Base model (llama3) available
- [x] OpenRouter integration working
- [x] Lane routing configured
- [x] SSH access via Tailscale

### Pending 🔄
- [ ] Pull coding-specific model (qwen2.5-coder:7b)
- [ ] Test Claude Code + Ollama integration
- [ ] Update lane config for local inference
- [ ] Benchmark local vs API performance
- [ ] Implement fallback logic
- [ ] Document model capabilities

### Blocked ⛔
- [ ] Claude Code model recognition for Ollama models
- [ ] Model override configuration not working

## Cost Analysis

### Current (OpenRouter)
- **Cost**: ~$0.75/1M tokens
- **Monthly estimate**: High usage pattern
- **Pros**: Reliable, no hardware cost
- **Cons**: Ongoing expense, balance concerns

### Target (Local Ollama)
- **Cost**: $0 after hardware
- **Hardware**: Already have GPU + 62GB RAM
- **Pros**: No ongoing cost, unlimited usage
- **Cons**: Setup complexity, model compatibility

## Next Steps

1. **Decision Point**: Keep OpenRouter or migrate to local?
2. **If local**: Resolve Claude Code model recognition
3. **If hybrid**: Implement fallback mechanism
4. **Testing**: Validate workflow with chosen approach

## Notes

- OpenRouter balance running low ($0.21)
- GLM-4.6 working well for coding tasks
- Local models need Claude Code compatibility work
- Consider hybrid approach as intermediate step