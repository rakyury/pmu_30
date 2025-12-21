# PMU-30 Configurator Tests

## Running Tests

### Run all tests
```bash
python -m unittest discover tests
```

### Run specific test file
```bash
python -m unittest tests.test_config_manager
```

### Run specific test case
```bash
python -m unittest tests.test_config_manager.TestConfigManager.test_add_input
```

### Run with verbose output
```bash
python -m unittest tests.test_config_manager -v
```

## Test Coverage

### ConfigManager Tests (test_config_manager.py)
- ✅ Initialization
- ✅ Configuration creation and retrieval
- ✅ Adding inputs/outputs (with max limit validation)
- ✅ Updating and deleting configurations
- ✅ Saving and loading from JSON files
- ✅ Modified state tracking
- ✅ Clearing configurations

## Adding New Tests

1. Create a new test file in `tests/` directory
2. Import unittest and the module to test
3. Create a test class inheriting from `unittest.TestCase`
4. Add test methods (must start with `test_`)
5. Use assertions to verify expected behavior

Example:
```python
import unittest
from models.my_module import MyClass

class TestMyClass(unittest.TestCase):
    def setUp(self):
        self.instance = MyClass()

    def test_something(self):
        result = self.instance.do_something()
        self.assertEqual(result, expected_value)
```
