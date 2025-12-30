"""
Test Professional UI workflow
Verify that add, edit, save, load functionality works correctly
"""

import sys
import json
import tempfile
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.config_manager import ConfigManager
from ui.widgets.project_tree import ProjectTree
from PyQt6.QtWidgets import QApplication

def test_workflow():
    """Test complete workflow."""
    print("Testing Professional UI workflow...")
    print("=" * 60)

    # Create Qt application (required for widgets)
    app = QApplication(sys.argv)

    # Create config manager and project tree
    config_manager = ConfigManager()
    project_tree = ProjectTree()

    print("\n1. Testing add operations...")

    # Add test output
    output_config = {
        "channel": 0,
        "name": "TestOutput1",
        "mode": "Normal",
        "pwm": {"enabled": False, "frequency": 1000, "duty_cycle": 50}
    }
    project_tree.add_output(output_config)
    print(f"   [OK] Added output: {output_config['name']}")

    # Add test input
    input_config = {
        "channel": 0,
        "name": "TestInput1",
        "type": "Switch Active High",
        "pullup": False
    }
    project_tree.add_input(input_config)
    print(f"   [OK] Added input: {input_config['name']}")

    # Add test logic function
    logic_config = {
        "name": "TestLogic1",
        "operation": "AND",
        "conditions": []
    }
    project_tree.add_logic_function(logic_config)
    print(f"   [OK] Added logic function: {logic_config['name']}")

    # Add test H-Bridge
    hbridge_config = {
        "name": "TestHBridge1",
        "mode": "Bidirectional",
        "control": {},
        "pwm": {},
        "protection": {}
    }
    project_tree.add_hbridge(hbridge_config)
    print(f"   [OK] Added H-Bridge: {hbridge_config['name']}")

    # Add test PID controller
    pid_config = {
        "name": "TestPID1",
        "parameters": {"kp": 1.0, "ki": 0.5, "kd": 0.1}
    }
    project_tree.add_pid_controller(pid_config)
    print(f"   [OK] Added PID controller: {pid_config['name']}")

    # Add test LUA script
    lua_config = {
        "name": "TestLua1",
        "script": "-- Test script",
        "trigger": {"type": "Periodic"}
    }
    project_tree.add_lua_script(lua_config)
    print(f"   [OK] Added LUA script: {lua_config['name']}")

    print("\n2. Testing getter methods...")

    # Get all data
    outputs = project_tree.get_all_outputs()
    inputs = project_tree.get_all_inputs()
    logic_functions = project_tree.get_all_logic_functions()
    hbridges = project_tree.get_all_hbridges()
    pid_controllers = project_tree.get_all_pid_controllers()
    lua_scripts = project_tree.get_all_lua_scripts()

    print(f"   [OK] Retrieved {len(outputs)} outputs")
    print(f"   [OK] Retrieved {len(inputs)} inputs")
    print(f"   [OK] Retrieved {len(logic_functions)} logic functions")
    print(f"   [OK] Retrieved {len(hbridges)} H-Bridges")
    print(f"   [OK] Retrieved {len(pid_controllers)} PID controllers")
    print(f"   [OK] Retrieved {len(lua_scripts)} LUA scripts")

    print("\n3. Testing save to config manager...")

    # Get config and update it
    config = config_manager.get_config()
    config["version"] = "1.0.0"
    config["device"]["name"] = "Test PMU-30"
    config["device"]["serial_number"] = "TEST001"
    config["outputs"] = outputs
    config["inputs"] = inputs
    config["logic_functions"] = logic_functions
    config["hbridge"] = hbridges
    config["pid_controllers"] = pid_controllers
    config["lua_scripts"] = lua_scripts
    config["can_messages"] = []
    config["settings"] = {}

    print("   [OK] Configuration set in config manager")

    print("\n4. Testing save to file...")

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_filename = temp_file.name
    temp_file.close()

    # Save to file
    success = config_manager.save_to_file(temp_filename)
    if success:
        print(f"   [OK] Saved to: {temp_filename}")
    else:
        print(f"   [FAIL] Failed to save to file")
        return False

    print("\n5. Testing load from file...")

    # Create new config manager and load
    new_config_manager = ConfigManager()
    success, error_msg = new_config_manager.load_from_file(temp_filename)

    if success:
        print(f"   [OK] Loaded from: {temp_filename}")
    else:
        print(f"   [FAIL] Failed to load: {error_msg}")
        return False

    print("\n6. Verifying data integrity...")

    loaded_config = new_config_manager.get_config()

    # Verify counts
    checks = [
        (len(loaded_config.get("outputs", [])), len(outputs), "outputs"),
        (len(loaded_config.get("inputs", [])), len(inputs), "inputs"),
        (len(loaded_config.get("logic_functions", [])), len(logic_functions), "logic functions"),
        (len(loaded_config.get("hbridge", [])), len(hbridges), "H-Bridges"),
        (len(loaded_config.get("pid_controllers", [])), len(pid_controllers), "PID controllers"),
        (len(loaded_config.get("lua_scripts", [])), len(lua_scripts), "LUA scripts"),
    ]

    all_passed = True
    for loaded_count, original_count, name in checks:
        if loaded_count == original_count:
            print(f"   [OK] {name}: {loaded_count} items (correct)")
        else:
            print(f"   [FAIL] {name}: expected {original_count}, got {loaded_count}")
            all_passed = False

    # Verify specific data
    if loaded_config["outputs"][0]["name"] == "TestOutput1":
        print(f"   [OK] Output name preserved: {loaded_config['outputs'][0]['name']}")
    else:
        print(f"   [FAIL] Output name mismatch")
        all_passed = False

    if loaded_config["inputs"][0]["name"] == "TestInput1":
        print(f"   [OK] Input name preserved: {loaded_config['inputs'][0]['name']}")
    else:
        print(f"   [FAIL] Input name mismatch")
        all_passed = False

    print("\n7. Testing update operation...")

    # Create new project tree and load data
    new_tree = ProjectTree()
    for output in loaded_config["outputs"]:
        new_tree.add_output(output)

    # Select first item and update it
    new_tree.tree.setCurrentItem(new_tree.out_folder.child(0))

    updated_output = output_config.copy()
    updated_output["name"] = "UpdatedOutput1"

    result = new_tree.update_current_item(updated_output)
    if result:
        print(f"   [OK] Updated item successfully")

        # Get updated data
        updated_outputs = new_tree.get_all_outputs()
        if updated_outputs[0]["name"] == "UpdatedOutput1":
            print(f"   [OK] Update reflected in data: {updated_outputs[0]['name']}")
        else:
            print(f"   [FAIL] Update not reflected")
            all_passed = False
    else:
        print(f"   [FAIL] Failed to update item")
        all_passed = False

    # Cleanup
    os.unlink(temp_filename)
    print(f"\n   [OK] Cleaned up temp file")

    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] All tests passed!")
        print("Professional UI workflow is working correctly.")
    else:
        print("[FAIL] Some tests failed!")
        print("Please review the output above.")

    return all_passed


if __name__ == "__main__":
    result = test_workflow()
    sys.exit(0 if result else 1)
