#!/usr/bin/env python3
"""
Verification script for Mistral-7B LLM integration.
Tests imports and basic functionality without requiring database connection.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all new modules import correctly."""
    print("Testing imports...")
    
    try:
        from llm.llm_schemas import AirClearance, GroundClearance
        print("✓ llm_schemas imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import llm_schemas: {e}")
        return False
    
    try:
        from llm.llm_prompts import build_air_prompt, build_ground_prompt
        print("✓ llm_prompts imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import llm_prompts: {e}")
        return False
    
    try:
        from llm.safety_validator import SafetyValidator
        print("✓ safety_validator imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import safety_validator: {e}")
        return False
    
    try:
        from llm.llm_dispatcher import (
            LLMDispatcher,
            AirLLMClient,
            GroundLLMClient,
            ContextBuilder,
            DecisionRouter,
        )
        print("✓ llm_dispatcher imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import llm_dispatcher: {e}")
        return False
    
    try:
        from llm import (
            LLMDispatcher,
            AirLLMClient,
            GroundLLMClient,
            AirClearance,
            GroundClearance,
            build_air_prompt,
            build_ground_prompt,
            SafetyValidator,
        )
        print("✓ llm package exports working correctly")
    except ImportError as e:
        print(f"✗ Failed to import from llm package: {e}")
        return False
    
    return True


def test_schemas():
    """Test schema creation and serialization."""
    print("\nTesting schemas...")
    
    from llm.llm_schemas import AirClearance, GroundClearance
    
    # Test AirClearance
    air_clearance = AirClearance(
        action_type="VECTORING",
        target_altitude_ft=10000,
        target_speed_kts=250,
        target_heading_deg=90,
        waypoints=None,
        runway=None
    )
    
    air_dict = air_clearance.to_dict()
    assert air_dict["action_type"] == "VECTORING"
    assert air_dict["target_altitude_ft"] == 10000
    assert "waypoints" not in air_dict  # None values filtered out
    print("✓ AirClearance schema working correctly")
    
    # Test GroundClearance
    ground_clearance = GroundClearance(
        action_type="GATE_ASSIGNMENT",
        assigned_gate="C32",
        taxi_route=["A1", "A", "B"],
        runway=None
    )
    
    ground_dict = ground_clearance.to_dict()
    assert ground_dict["action_type"] == "GATE_ASSIGNMENT"
    assert ground_dict["assigned_gate"] == "C32"
    assert len(ground_dict["taxi_route"]) == 3
    assert "runway" not in ground_dict  # None values filtered out
    print("✓ GroundClearance schema working correctly")
    
    return True


def test_prompts():
    """Test prompt generation."""
    print("\nTesting prompts...")
    
    from llm.llm_prompts import build_air_prompt, build_ground_prompt
    
    # Test air prompt
    air_context = {
        "aircraft_id": 123,
        "current_zone": "APPROACH_5",
        "aircraft": {
            "callsign": "UAL123",
            "altitude_ft": 5000,
            "speed_kts": 220,
            "heading": 50,
            "distance_to_airport_nm": 8.5,
        },
        "current_zone_aircraft": [
            {"callsign": "AAL456", "distance_nm": 7.2},
            {"callsign": "DAL789", "distance_nm": 9.1},
        ]
    }
    
    air_prompt = build_air_prompt(air_context)
    assert "UAL123" in air_prompt
    assert "APPROACH_5" in air_prompt
    assert "3NM" in air_prompt  # Hard rule mentioned
    assert "JSON" in air_prompt  # JSON output required
    print("✓ Air prompt generated correctly")
    
    # Test ground prompt
    ground_context = {
        "aircraft_id": 456,
        "event_type": "runway.landed",
        "aircraft": {
            "callsign": "SWA321",
            "phase": "ROLLOUT",
        }
    }
    
    ground_prompt = build_ground_prompt(ground_context)
    assert "SWA321" in ground_prompt
    assert "runway.landed" in ground_prompt
    assert "JSON" in ground_prompt  # JSON output required
    print("✓ Ground prompt generated correctly")
    
    return True


def test_ollama_available():
    """Test if Ollama is installed and Mistral model is available."""
    print("\nChecking Ollama installation...")
    
    import subprocess
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print("✗ Ollama is not running or not installed")
            print("  Install: curl -fsSL https://ollama.com/install.sh | sh")
            return False
        
        if "mistral" in result.stdout.lower():
            print("✓ Ollama installed with Mistral model")
            return True
        else:
            print("⚠ Ollama installed but Mistral model not found")
            print("  Run: ollama pull mistral")
            return False
            
    except FileNotFoundError:
        print("✗ Ollama command not found")
        print("  Install: curl -fsSL https://ollama.com/install.sh | sh")
        return False
    except Exception as e:
        print(f"⚠ Could not verify Ollama: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Mistral-7B LLM Integration Verification")
    print("=" * 60)
    print()
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test schemas
    try:
        results.append(("Schemas", test_schemas()))
    except Exception as e:
        print(f"✗ Schema tests failed: {e}")
        results.append(("Schemas", False))
    
    # Test prompts
    try:
        results.append(("Prompts", test_prompts()))
    except Exception as e:
        print(f"✗ Prompt tests failed: {e}")
        results.append(("Prompts", False))
    
    # Test Ollama
    results.append(("Ollama", test_ollama_available()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20s}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("✅ All verification tests passed!")
        print("The LLM integration is ready to use.")
        return 0
    else:
        print("⚠️  Some verification tests failed.")
        print("Please fix the issues above before running the LLM dispatcher.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

