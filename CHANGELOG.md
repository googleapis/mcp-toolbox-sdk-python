# Changelog

## [1.0.0](https://github.com/googleapis/genai-toolbox-langchain-python/compare/v0.1.0...v1.0.0) (2025-04-04)


### ⚠ BREAKING CHANGES

* Improve response handling from Toolbox server ([#69](https://github.com/googleapis/genai-toolbox-langchain-python/issues/69))

### Features

* Add support for checking tool-level auth before tool invocation. ([#72](https://github.com/googleapis/genai-toolbox-langchain-python/issues/72)) ([82c6836](https://github.com/googleapis/genai-toolbox-langchain-python/commit/82c6836e85d4474787c1e0225d3e7f74fe4b7662))
* Add type validation to params when tool is invoked ([#129](https://github.com/googleapis/genai-toolbox-langchain-python/issues/129)) ([5d62138](https://github.com/googleapis/genai-toolbox-langchain-python/commit/5d621388b3dc8d6fb7583b56dc9d7fcfa02c0a8b))
* Added a sync toolbox client ([#131](https://github.com/googleapis/genai-toolbox-langchain-python/issues/131)) ([ed82832](https://github.com/googleapis/genai-toolbox-langchain-python/commit/ed82832b6e84e8e278820b537fbdbfabd1a0b250))
* **toolbox-core:** Add authenticated parameters support ([#119](https://github.com/googleapis/genai-toolbox-langchain-python/issues/119)) ([10087a1](https://github.com/googleapis/genai-toolbox-langchain-python/commit/10087a136056cd47765b376ba18897bae5b848a3))
* **toolbox-core:** Add basic implementation  ([#103](https://github.com/googleapis/genai-toolbox-langchain-python/issues/103)) ([4f992d8](https://github.com/googleapis/genai-toolbox-langchain-python/commit/4f992d8b2d3cc75692d030b67d13f90c36c49ac9))
* **toolbox-core:** Add support for bound parameters ([#120](https://github.com/googleapis/genai-toolbox-langchain-python/issues/120)) ([b2a2208](https://github.com/googleapis/genai-toolbox-langchain-python/commit/b2a22089d4a9abc067605d603c077ff4c4843147))
* **toolbox-core:** Updated generated docstring to include parameters and their descriptions ([#127](https://github.com/googleapis/genai-toolbox-langchain-python/issues/127)) ([eafe2e9](https://github.com/googleapis/genai-toolbox-langchain-python/commit/eafe2e9cb1e2f84e3b2ba5bee5c469ae5754ade9))


### Bug Fixes

* Add items to parameter schema ([#62](https://github.com/googleapis/genai-toolbox-langchain-python/issues/62)) ([d77eb7c](https://github.com/googleapis/genai-toolbox-langchain-python/commit/d77eb7c4ccf604ea8449a784d6ba4d8b4ad1ac96))
* Add qualname for ToolboxTool instances ([#134](https://github.com/googleapis/genai-toolbox-langchain-python/issues/134)) ([5c2dff7](https://github.com/googleapis/genai-toolbox-langchain-python/commit/5c2dff7b2378eaa9298cc281b3658f85a32aa1a5))
* Correct invalid reference when using array types ([#128](https://github.com/googleapis/genai-toolbox-langchain-python/issues/128)) ([d5a3259](https://github.com/googleapis/genai-toolbox-langchain-python/commit/d5a325926e3fb03b33f9133e7cc70fa935b9aecb))
* **deps:** Update dependency black to v25 ([#47](https://github.com/googleapis/genai-toolbox-langchain-python/issues/47)) ([451c0b1](https://github.com/googleapis/genai-toolbox-langchain-python/commit/451c0b18287fa003b3e10e531b45a82b16ea0c5b))
* **deps:** Update dependency google-cloud-storage to v3 ([#48](https://github.com/googleapis/genai-toolbox-langchain-python/issues/48)) ([ecdecb7](https://github.com/googleapis/genai-toolbox-langchain-python/commit/ecdecb7921354cd1fc98e04d5133c262b958d0c4))
* **deps:** Update dependency isort to v6 ([#49](https://github.com/googleapis/genai-toolbox-langchain-python/issues/49)) ([313f6d3](https://github.com/googleapis/genai-toolbox-langchain-python/commit/313f6d3e3df0728530f106005d5e5bd49f3be519))
* **deps:** Update dependency pillow to v11 ([#50](https://github.com/googleapis/genai-toolbox-langchain-python/issues/50)) ([955fd41](https://github.com/googleapis/genai-toolbox-langchain-python/commit/955fd41e32d0d33280640ba5bf974e284e427f95))
* **deps:** Update python-nonmajor ([#30](https://github.com/googleapis/genai-toolbox-langchain-python/issues/30)) ([93240a2](https://github.com/googleapis/genai-toolbox-langchain-python/commit/93240a2de5e5ef7f98ecf9b7de81b31b2104d5e4))
* **deps:** Update python-nonmajor ([#93](https://github.com/googleapis/genai-toolbox-langchain-python/issues/93)) ([2d7d095](https://github.com/googleapis/genai-toolbox-langchain-python/commit/2d7d0958429f60052a53758edf35d087d040280b))
* **deps:** Update python-nonmajor ([#98](https://github.com/googleapis/genai-toolbox-langchain-python/issues/98)) ([f03e7ec](https://github.com/googleapis/genai-toolbox-langchain-python/commit/f03e7ec986eddfb1e0adc81b8be8e9140dcbd530))
* Improve response handling from Toolbox server ([#69](https://github.com/googleapis/genai-toolbox-langchain-python/issues/69)) ([f4935c0](https://github.com/googleapis/genai-toolbox-langchain-python/commit/f4935c09592ec907d49fd771a30fe5b1e085a2f0))
* **langchain-sdk:** Fix issue occurring when using a tool with list type. ([#33](https://github.com/googleapis/genai-toolbox-langchain-python/issues/33)) ([9c4f0d1](https://github.com/googleapis/genai-toolbox-langchain-python/commit/9c4f0d102e9d399437e67152e906a76d9d632757))
* Make all fields required in Tool schema ([#68](https://github.com/googleapis/genai-toolbox-langchain-python/issues/68)) ([c2b52aa](https://github.com/googleapis/genai-toolbox-langchain-python/commit/c2b52aa9df07cf78ef794933bac491b139515d92))


### Documentation

* Update syntax error on readme ([#121](https://github.com/googleapis/genai-toolbox-langchain-python/issues/121)) ([cd6d76d](https://github.com/googleapis/genai-toolbox-langchain-python/commit/cd6d76de62d60b343089d590e078ee7c01037af2))
