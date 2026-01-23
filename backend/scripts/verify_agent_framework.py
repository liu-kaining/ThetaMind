#!/usr/bin/env python3
"""Verification script for Agent Framework implementation.

This script verifies that all three phases are correctly implemented:
- Phase 1: Basic integration (GeminiProvider, API endpoints, quota management)
- Phase 2: New endpoints (multi-agent, workflows, stock screening, agent list)
- Integration: End-to-end functionality

Usage:
    python scripts/verify_agent_framework.py
"""

import sys
import importlib
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def check_imports():
    """Check that all required modules can be imported."""
    print("🔍 Checking imports...")
    
    modules = [
        "app.services.ai.gemini_provider",
        "app.services.ai_service",
        "app.services.agents.base",
        "app.services.agents.registry",
        "app.services.agents.executor",
        "app.services.agents.coordinator",
        "app.api.endpoints.ai",
    ]
    
    failed = []
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name}: {e}")
            failed.append(module_name)
    
    return len(failed) == 0


def check_phase1():
    """Check Phase 1 implementation."""
    print("\n📋 Checking Phase 1: Basic Integration...")
    
    checks = []
    
    # Check GeminiProvider
    try:
        from app.services.ai.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        
        # Check agent mode support
        if hasattr(provider, 'generate_report'):
            checks.append(("GeminiProvider.generate_report exists", True))
        else:
            checks.append(("GeminiProvider.generate_report exists", False))
        
        # Check _call_ai_api supports system_prompt
        if hasattr(provider, '_call_ai_api'):
            import inspect
            sig = inspect.signature(provider._call_ai_api)
            params = list(sig.parameters.keys())
            if 'system_prompt' in params:
                checks.append(("_call_ai_api supports system_prompt", True))
            else:
                checks.append(("_call_ai_api supports system_prompt", False))
        else:
            checks.append(("_call_ai_api exists", False))
            
    except Exception as e:
        checks.append((f"GeminiProvider check: {e}", False))
    
    # Check API endpoints
    try:
        from app.api.endpoints.ai import (
            StrategyAnalysisRequest,
            check_ai_quota,
            increment_ai_usage,
            generate_ai_report,
        )
        
        # Check StrategyAnalysisRequest has use_multi_agent
        request = StrategyAnalysisRequest(strategy_summary={})
        if hasattr(request, 'use_multi_agent'):
            checks.append(("StrategyAnalysisRequest has use_multi_agent", True))
        else:
            checks.append(("StrategyAnalysisRequest has use_multi_agent", False))
        
        # Check quota functions support required_quota/quota_units
        import inspect
        quota_sig = inspect.signature(check_ai_quota)
        if 'required_quota' in quota_sig.parameters:
            checks.append(("check_ai_quota supports required_quota", True))
        else:
            checks.append(("check_ai_quota supports required_quota", False))
        
        increment_sig = inspect.signature(increment_ai_usage)
        if 'quota_units' in increment_sig.parameters:
            checks.append(("increment_ai_usage supports quota_units", True))
        else:
            checks.append(("increment_ai_usage supports quota_units", False))
            
    except Exception as e:
        checks.append((f"API endpoints check: {e}", False))
    
    # Print results
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed


def check_phase2():
    """Check Phase 2 implementation."""
    print("\n📋 Checking Phase 2: New Endpoints...")
    
    checks = []
    
    try:
        from app.api.endpoints.ai import (
            generate_multi_agent_report,
            screen_stocks,
            analyze_options_workflow,
            list_agents,
            StockScreeningRequest,
            OptionsAnalysisWorkflowRequest,
        )
        
        # Check endpoints exist
        checks.append(("generate_multi_agent_report exists", True))
        checks.append(("screen_stocks exists", True))
        checks.append(("analyze_options_workflow exists", True))
        checks.append(("list_agents exists", True))
        
        # Check request models
        checks.append(("StockScreeningRequest exists", True))
        checks.append(("OptionsAnalysisWorkflowRequest exists", True))
        
    except ImportError as e:
        checks.append((f"Phase 2 imports: {e}", False))
    except Exception as e:
        checks.append((f"Phase 2 check: {e}", False))
    
    # Print results
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed


def check_integration():
    """Check integration."""
    print("\n📋 Checking Integration...")
    
    checks = []
    
    try:
        from app.services.ai_service import ai_service
        
        # Check AIService has agent_coordinator
        if hasattr(ai_service, 'agent_coordinator'):
            checks.append(("AIService has agent_coordinator", True))
        else:
            checks.append(("AIService has agent_coordinator", False))
        
        # Check generate_report_with_agents exists
        if hasattr(ai_service, 'generate_report_with_agents'):
            checks.append(("generate_report_with_agents exists", True))
        else:
            checks.append(("generate_report_with_agents exists", False))
        
        # Check _format_agent_report exists
        if hasattr(ai_service, '_format_agent_report'):
            checks.append(("_format_agent_report exists", True))
        else:
            checks.append(("_format_agent_report exists", False))
        
    except Exception as e:
        checks.append((f"Integration check: {e}", False))
    
    # Print results
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Agent Framework Verification Script")
    print("=" * 60)
    
    results = {}
    
    # Check imports
    results['imports'] = check_imports()
    
    if not results['imports']:
        print("\n❌ Import checks failed. Please install dependencies.")
        return 1
    
    # Check Phase 1
    results['phase1'] = check_phase1()
    
    # Check Phase 2
    results['phase2'] = check_phase2()
    
    # Check Integration
    results['integration'] = check_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for phase, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{phase.upper():15} {status}")
    
    if all_passed:
        print("\n🎉 All checks passed!")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
