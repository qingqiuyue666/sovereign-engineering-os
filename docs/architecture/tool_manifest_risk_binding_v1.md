# Tool Manifest Risk Binding V1

Tool Manifest Risk Binding V1 connects `NormalizedToolManifest` records to the
existing Tool Risk Classifier.

The binding converts normalized manifest metadata into `ToolRiskDescriptor`
instances and delegates risk assessment to `classify_tool_risk`. It does not
duplicate classifier logic, execute tools, contact MCP servers, call provider
APIs, access the network, launch browsers, launch DCC applications, or load
ComfyUI workflows.

The binding adds source-type hints that make dry-run manifest origin visible to
the classifier:

- `MCP_TOOL` and `MCP_SERVER` imply MCP tool risk.
- `DCC_APP` implies DCC control risk.
- `COMFYUI_WORKFLOW` implies ComfyUI execution risk and model execution when a
  model scope is declared.
- `BROWSER_AUTOMATION_TOOL` implies browser control risk.
- `API_ADAPTER` with provider scope implies provider API risk.
- credential scope implies credential touching and high risk.
- `UNKNOWN` source type fails closed through high risk.

The report records the manifest content hash, risk assessment content hash, and
a deterministic binding hash that excludes only `observed_at`.

Even if a low-risk descriptor is produced, production admission remains false in
this binding because Tool Manifest Normalizer V1 does not grant direct execution
or runtime integration.
