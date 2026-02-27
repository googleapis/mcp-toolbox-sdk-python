# Changelog

## [0.6.1](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-adk-v0.6.0...toolbox-adk-v0.6.1) (2026-02-27)


### Bug Fixes

* **core:** Recursive schema parsing for array items with MCP transport ([#561](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/561)) ([09eb555](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/09eb5554cf265a608e55b559b185b686c88c34aa))

## [0.6.0](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-adk-v0.5.8...toolbox-adk-v0.6.0) (2026-02-16)


### ⚠ BREAKING CHANGES

* **adk:** remove pre/post processing functionality ([#539](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/539))

### Features

* **adk:** remove pre/post processing functionality ([#539](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/539)) ([36953cf](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/36953cff75ce2e11c8f69f4ad9139eec8ef2fc44))
* Deprecate Protocol.TOOLBOX (Native HTTP Protocol) ([#547](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/547)) ([b99ec50](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/b99ec503bb5d85e6bdf84f72343d90ac00ab8d88))
* Enable package-specific client identification for MCP ([#525](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/525)) ([7ac0d3f](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/7ac0d3f167af1e47c26a3f43bdb48f3fc0a92109))


### Bug Fixes

* **adk:** Add float type parsing and required field None handling ([#549](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/549)) ([4302b80](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/4302b804bc5ea9faa25c58badb0197b2b2153d43))
* **adk:** implement `_get_declaration` to natively support ADK schema builder ([#534](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/534)) ([4f11229](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/4f112293becf3dc7c0e2f44cb7754a1eb8e45def))
* **adk:** resolve OAuth persistence, ID token extraction, and auth flow crashes ([#535](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/535)) ([663a4e1](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/663a4e144b039207ef66b512d6287f9e520435de))


### Miscellaneous Chores

* decouple toolbox-core dependency versioning ([#550](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/550)) ([b8163fe](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/b8163feab0d35aa915213e640200da07c101127a))
* **deps:** update mcp toolbox server version in integration tests to v0.27.0 to v0.27.0 ([#545](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/545)) ([851c7b5](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/851c7b542a18cd634b943d47b5b5331ac19dcd5b))
* Fix issue with release PR presubmits not picking latest changes from orch packages ([#548](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/548)) ([8b0db22](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/8b0db22d55453c963ba726b639922085ef77db20))
* optimize CI dependency resolution to prevent PyPI version conflicts ([#546](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/546)) ([7c4a608](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/7c4a608734042e0d501bbe351ad0c0e295cfe909))


### Documentation

* Update README with simplified ADK import paths and modernized type hints in code examples ([#537](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/537)) ([8e7ea07](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/8e7ea0745de565729d6bfcb5708b7a8473a54f9e))

## [0.5.8](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-adk-v0.5.7...toolbox-adk-v0.5.8) (2026-01-29)

### Features

* **mcp:** add MCP v20251125 ([#507](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/507)) ([9c2d264](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/9c2d2649066f0034c6f66f08d3edc11193c75a3d))
  * **mcp:** keep v20250618 the default mcp protocol ([#520](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/520)) ([ec791a5](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/ec791a55a9f7ac6b9954bb805a369e4b6db06766))

### Documentation

* **adk:** add transport protocols section ([#521](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/521)) ([2158f0e](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/2158f0e2b504d7d5ce5e6dd043c08e4956cdd02d))

> [!NOTE]
> For additional changelogs of the underlying `toolbox-core` package, visit: https://github.com/googleapis/mcp-toolbox-sdk-python/releases/tag/toolbox-core-v0.5.8


## [0.5.7](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-adk-v0.5.6...toolbox-adk-v0.5.7) (2026-01-13)


### Features

* enable Python 3.14 support ([#494](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/494)) ([0ced95b](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/0ced95bcd7694f76e9bfc5166fbe9c0c260ca54a))


### Miscellaneous Chores

* replace pip with uv for 60% faster integration tests ([#495](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/495)) ([fbc3f54](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/fbc3f54bf1bf00c1acd9cdedc0c3cf0e8a3566c3))


## [0.5.6](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-adk-v0.0.1...toolbox-adk-v0.5.6) (2026-01-08)


### Features

* **toolbox-adk:** Implement tool wrapper & auth getters ([#457](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/457)) ([b08f511](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/b08f5117f59d77256584078ad0d6831bc1ae0bd4))
* **toolbox-adk:** Develop the internal ToolboxClient wrapper ([#456](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/456)) ([4d18953](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/4d18953f58c4497d51b67e711ad652b65c3c64cd))
* **toolbox-adk:** Implement core data classes ([#455](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/455)) ([3d02ea1](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/3d02ea182255cb7e14e5935ebd0000f34fc70e26))
* **toolbox-adk:** Package scaffolding & setup ([#454](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/454)) ([fb5dfb5](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/fb5dfb5d7b129f197bee9aa6f280ff73b3dd30fa))
* **toolbox-adk:** Add ADK credential factories & simplify Toolset init ([#473](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/473)) ([30b21ab](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/30b21ab2d4771e8fdd83755d9140bab8c25c9b75))
* **toolbox-adk:** Add ADK credential factory methods ([#463](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/463)) ([e8092c4](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/e8092c42f546696b2411c89bd19ff30a2299c16a))


### Documentation

* **toolbox-adk:** Polish `README` with comprehensive examples ([#464](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/464)) ([a52591c](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/a52591c9ede7dfa671473e27d5b5adef604f0db5))
