# Plugin API Specification

The Plugin API dictates how third-party capabilities are securely loaded into the Chhaya AI OS.

## 1. Plugin Lifecycle
1.  **Discovery:** The PluginManager scans `plugins/*/manifest.json`.
2.  **Resolution:** Checks `manifest.json` for dependencies and kernel version compatibility.
3.  **Instantiation:** The Python module is imported, and the class inheriting from `plugin_sdk.Plugin` is instantiated.
4.  **Registration:** `plugin.register(registry, event_bus)` is called. The plugin mounts its providers or event listeners.
5.  **Activation:** The plugin is marked as active.
6.  **Deactivation/Unloading:** `plugin.shutdown()` is called during system shutdown or hot-reloading.

## 2. Capability Declaration
A plugin must declare its capabilities in its `manifest.json`. This acts as a security boundary.

```json
{
  "name": "chhaya-anthropic-provider",
  "version": "1.0.0",
  "author": "Community",
  "kernel_version": ">=0.1.0",
  "capabilities": {
    "provides": ["LLMProvider"],
    "requires": ["ConfigManager"]
  },
  "permissions": [
    "network.outbound:api.anthropic.com"
  ],
  "entrypoint": "main:AnthropicPlugin"
}
```

## 3. Registration API
The `Plugin` base class provides a standard interface:

```python
from chhaya.plugin_sdk import Plugin, Registry, EventBus

class MyPlugin(Plugin):
    def register(self, registry: Registry, bus: EventBus) -> None:
        # Register a concrete provider
        registry.register_llm_provider("anthropic", AnthropicProvider())

        # Or register a tool
        registry.register_tool("web_search", WebSearchTool())

        # Or listen to events
        bus.subscribe("agent.task.completed", self.on_task_complete)
```

## 4. Permission Model
Plugins operate under a Principle of Least Privilege:
1.  **Network Access:** Explicitly requested in the manifest. (Enforced in Phase 5 via sandboxing, but strictly audited now).
2.  **File System:** Tools must request `fs.read` or `fs.write` scopes, which the PermissionManager validates.
3.  **Event Masking:** By default, plugins can only subscribe to `*.completed` events to prevent them from intercepting or cancelling core kernel `*.requested` events unless they have the `kernel.intercept` permission.

## 5. Dependency System
Plugins can depend on other plugins or core kernel packages.
*   The `PluginManager` builds a Directed Acyclic Graph (DAG) of dependencies during boot.
*   If Plugin B requires Plugin A, Plugin A is loaded and initialized first.
*   If cyclic dependencies are detected, the Kernel boot aborts and logs a critical error.