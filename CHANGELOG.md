# Changelog

## 0.1.0 (2025-02-05)


### ⚠ BREAKING CHANGES

* Improve PyPI package name. ([#17](https://github.com/googleapis/genai-toolbox-langchain-python/issues/17))
* **langchain-sdk:** Migrate existing state and APIs to a tools level class. ([#171](https://github.com/googleapis/genai-toolbox-langchain-python/issues/171))
* **toolbox-sdk:** deprecate 'add_auth_headers' in favor of 'add_auth_tokens'  ([#170](https://github.com/googleapis/genai-toolbox-langchain-python/issues/170))

### Features

* Add support for sync operations ([#15](https://github.com/googleapis/genai-toolbox-langchain-python/issues/15)) ([9885469](https://github.com/googleapis/genai-toolbox-langchain-python/commit/9885469703d88afc7c7aed10c85e97c099d7e532))
* **langchain-sdk:** Add features for binding parameters to ToolboxTool class. ([#192](https://github.com/googleapis/genai-toolbox-langchain-python/issues/192)) ([4fcfc35](https://github.com/googleapis/genai-toolbox-langchain-python/commit/4fcfc3549038c52c495d452f36037817a30eed2e))
* **langchain-sdk:** Add Toolbox SDK for LangChain ([#22](https://github.com/googleapis/genai-toolbox-langchain-python/issues/22)) ([d4a24e6](https://github.com/googleapis/genai-toolbox-langchain-python/commit/d4a24e66139cb985d7457d9162766ce564c36656))
* **langchain-sdk:** Correctly parse Manifest API response as JSON ([#143](https://github.com/googleapis/genai-toolbox-langchain-python/issues/143)) ([86bcf1c](https://github.com/googleapis/genai-toolbox-langchain-python/commit/86bcf1c4db65aa5214f4db280d55cfc23edac361))
* **langchain-sdk:** Migrate existing state and APIs to a tools level class. ([#171](https://github.com/googleapis/genai-toolbox-langchain-python/issues/171)) ([6fe2e39](https://github.com/googleapis/genai-toolbox-langchain-python/commit/6fe2e39eb16eeeeaedea0a31fc2125b105d633b4))
* **langchain-sdk:** Support authentication in LangChain Toolbox SDK. ([#133](https://github.com/googleapis/genai-toolbox-langchain-python/issues/133)) ([b28bdb5](https://github.com/googleapis/genai-toolbox-langchain-python/commit/b28bdb5b12cdfe3fe6768345c00a65a65d91b81b))
* **llamaindex-sdk:** Implement OAuth support for LlamaIndex. ([#159](https://github.com/googleapis/genai-toolbox-langchain-python/issues/159)) ([dc47da9](https://github.com/googleapis/genai-toolbox-langchain-python/commit/dc47da9282af876939f60d6b24e5a9cf3bf75dfd))
* **sdk:** Make ClientSession optional when initializing ToolboxClient ([#55](https://github.com/googleapis/genai-toolbox-langchain-python/issues/55)) ([956591d](https://github.com/googleapis/genai-toolbox-langchain-python/commit/956591d1da69495df3f602fd9e5fd967bd7ea5ca))


### Bug Fixes

* **docs:** Correct outdated references to tool kinds ([#49](https://github.com/googleapis/genai-toolbox-langchain-python/issues/49)) ([da26916](https://github.com/googleapis/genai-toolbox-langchain-python/commit/da269162dd62b6197a34554a5414cc8070f9c525))
* Fix issue causing client session to not close properly while closing SDK. ([#81](https://github.com/googleapis/genai-toolbox-langchain-python/issues/81)) ([748fad4](https://github.com/googleapis/genai-toolbox-langchain-python/commit/748fad4cb0b8bac5f5cc5a7b5cc015b9491c25cd))
* Fix the errors showing up after setting up mypy type checker. ([#74](https://github.com/googleapis/genai-toolbox-langchain-python/issues/74)) ([0384114](https://github.com/googleapis/genai-toolbox-langchain-python/commit/0384114caad4b4ba42db6cd082a9185ff160a055))
* Improve PyPI package name. ([#17](https://github.com/googleapis/genai-toolbox-langchain-python/issues/17)) ([cd95f3e](https://github.com/googleapis/genai-toolbox-langchain-python/commit/cd95f3e2bcc884436e1c13fbd4f654fc67c7d7fc))
* **langchain-sdk:** Correct test name to ensure execution and full coverage. ([#145](https://github.com/googleapis/genai-toolbox-langchain-python/issues/145)) ([b95bb90](https://github.com/googleapis/genai-toolbox-langchain-python/commit/b95bb901ac79cb40661d0da1847b00fcdfd89532))
* **langchain-sdk:** Inherit from BaseTool and implement placeholder _run method. ([f6f7af9](https://github.com/googleapis/genai-toolbox-langchain-python/commit/f6f7af9b9c9885c2a869051379b6c3bd34f4e118))
* Schema float type ([#14](https://github.com/googleapis/genai-toolbox-langchain-python/issues/14)) ([e259642](https://github.com/googleapis/genai-toolbox-langchain-python/commit/e259642af177b60ee713aa38fa133ab813efe707))
* **toolbox-sdk:** Deprecate 'add_auth_headers' in favor of 'add_auth_tokens'  ([#170](https://github.com/googleapis/genai-toolbox-langchain-python/issues/170)) ([c5c699c](https://github.com/googleapis/genai-toolbox-langchain-python/commit/c5c699cc29bcc0708a31bff90e8cec489982fe2a))


### Documentation

* **langchain-sdk:** Update README file ([#54](https://github.com/googleapis/genai-toolbox-langchain-python/issues/54)) ([79e8303](https://github.com/googleapis/genai-toolbox-langchain-python/commit/79e83030c6bc85b3b7d31b471b81e289da5c58a5))


### Miscellaneous Chores

* Release 0.1.0 ([#24](https://github.com/googleapis/genai-toolbox-langchain-python/issues/24)) ([6fff8e2](https://github.com/googleapis/genai-toolbox-langchain-python/commit/6fff8e2ea18bd6df9f30d7790b6076cf0b32cc75))
