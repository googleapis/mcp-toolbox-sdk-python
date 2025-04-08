# Changelog

## [0.1.1](https://github.com/googleapis/genai-toolbox-langchain-python/compare/toolbox-langchain-v0.1.0...toolbox-langchain-v0.1.1) (2025-04-08)


### Bug Fixes

* **deps:** update python-nonmajor ([#148](https://github.com/googleapis/genai-toolbox-langchain-python/issues/148)) ([bc894e1](https://github.com/googleapis/genai-toolbox-langchain-python/commit/bc894e1d14823e88a3c0f24ab05b8839a3d653e0))
* **deps:** update python-nonmajor ([#98](https://github.com/googleapis/genai-toolbox-langchain-python/issues/98)) ([f03e7ec](https://github.com/googleapis/genai-toolbox-langchain-python/commit/f03e7ec986eddfb1e0adc81b8be8e9140dcbd530))


### Miscellaneous Chores

* change port number to default toolbox port ([#135](https://github.com/googleapis/genai-toolbox-langchain-python/issues/135)) ([6164b09](https://github.com/googleapis/genai-toolbox-langchain-python/commit/6164b09d60412a0e3faf95c1b2e8df13b5ab7782))
* fix urls in pyproject.toml ([#101](https://github.com/googleapis/genai-toolbox-langchain-python/issues/101)) ([6e5875e](https://github.com/googleapis/genai-toolbox-langchain-python/commit/6e5875eb5c3dbce9c9efb00418716577f90e4d05))
* **main:** release toolbox-langchain 0.1.1 ([#54](https://github.com/googleapis/genai-toolbox-langchain-python/issues/54)) ([3e4edf1](https://github.com/googleapis/genai-toolbox-langchain-python/commit/3e4edf12841ed880073ac0e4e905a51c4cc7c9a9))
* refactor layout for multiple packages ([#99](https://github.com/googleapis/genai-toolbox-langchain-python/issues/99)) ([ac43090](https://github.com/googleapis/genai-toolbox-langchain-python/commit/ac43090822fbf19a8920732e2ec3aa8b9c3130c1))

## 0.1.0 (2025-02-05)


### ⚠ BREAKING CHANGES

* Improve PyPI package name
* Migrate existing state and APIs to a tools level class
* deprecate 'add_auth_headers' in favor of 'add_auth_tokens' 

### Features

* Add support for sync operations ([9885469](https://github.com/googleapis/genai-toolbox-langchain-python/commit/9885469703d88afc7c7aed10c85e97c099d7e532))
*Add features for binding parameters to ToolboxTool class. ([4fcfc35](https://github.com/googleapis/genai-toolbox-langchain-python/commit/4fcfc3549038c52c495d452f36037817a30eed2e))
*Add Toolbox SDK for LangChain ([d4a24e6](https://github.com/googleapis/genai-toolbox-langchain-python/commit/d4a24e66139cb985d7457d9162766ce564c36656))
* Correctly parse Manifest API response as JSON ([86bcf1c](https://github.com/googleapis/genai-toolbox-langchain-python/commit/86bcf1c4db65aa5214f4db280d55cfc23edac361))
* Migrate existing state and APIs to a tools level class. ([6fe2e39](https://github.com/googleapis/genai-toolbox-langchain-python/commit/6fe2e39eb16eeeeaedea0a31fc2125b105d633b4))
* Support authentication in LangChain Toolbox SDK. ([b28bdb5](https://github.com/googleapis/genai-toolbox-langchain-python/commit/b28bdb5b12cdfe3fe6768345c00a65a65d91b81b))
* Implement OAuth support for LlamaIndex. ([dc47da9](https://github.com/googleapis/genai-toolbox-langchain-python/commit/dc47da9282af876939f60d6b24e5a9cf3bf75dfd))
* Make ClientSession optional when initializing ToolboxClient ([956591d](https://github.com/googleapis/genai-toolbox-langchain-python/commit/956591d1da69495df3f602fd9e5fd967bd7ea5ca))


### Bug Fixes

* Deprecate 'add_auth_headers' in favor of 'add_auth_tokens' ([c5c699c](https://github.com/googleapis/genai-toolbox-langchain-python/commit/c5c699cc29bcc0708a31bff90e8cec489982fe2a))
