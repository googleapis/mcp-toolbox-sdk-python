# Changelog

## [0.5.1](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-core-v0.5.0...toolbox-core-v0.5.1) (2025-09-17)


### Bug Fixes

* **toolbox-core:** Use typing.Annotated for reliable parameter descriptions instead of docstrings ([#371](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/371)) ([eb76680](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/eb76680d24c344241f3c15293cd12904bbf91b0d))


### Documentation

* Update langgraph sample in toolbox-core ([#366](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/366)) ([fe35082](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/fe35082104d8039986eccbdab937f5f3e8b2042b))


### Miscellaneous Chores

* Remove redundant test for test_add_auth_token_getter_unused_token ([#347](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/347)) ([dccaf1b](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/dccaf1bd70e4e788fd80a9ef952aede4549b2fc7))
* Remove duplicate header check during initialization ([#357](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/357)) ([888170b](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/888170b3c34744089fb3b6f2b6f613c4cd718a89))


## [0.5.0](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-core-v0.4.0...toolbox-core-v0.5.0) (2025-08-19)


### ⚠ BREAKING CHANGES

* **core:** Use ValueError for missing 'items' in array parameters ([#325](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/325))

### Features

* **core:** Add support for map parameter type ([#324](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/324)) ([6455ae3](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/6455ae3b88774e7cd79f5c348e9f44bfc5424a18))


### Bug Fixes

* add optional clock_skew parameter to token helpers ([#333](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/333)) ([aa0664f](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/aa0664ff6d88d83bba4fc1a8ffe4766e4e8c8aa3))
* **core:** Use ValueError for missing 'items' in array parameters ([#325](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/325)) ([b43409e](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/b43409ed220bbe89ab2521286239af203c067897))


### Documentation

* Enhance DEVELOPER.md for improved contribution guidelines ([#316](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/316)) ([1d2be43](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/1d2be4396d50d1119381149c7b1c4d1a778a0349))


## [0.4.0](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-core-v0.3.0...toolbox-core-v0.4.0) (2025-07-17)


### ⚠ BREAKING CHANGES

*  **toolbox-core:** fix auth_methods module ([#313](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/313))

### Bug Fixes

*  **toolbox-core:** fix auth_methods module ([#313](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/313)) ([6cf6d6b](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/6cf6d6ba3cd67d7c4e18e919a10c37f34971dcf1))
  

## [0.3.0](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-core-v0.2.1...toolbox-core-v0.3.0) (2025-07-02)


### Features

* **toolbox-core:** Add support for optional parameters ([#290](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/290)) ([3c8360c](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/3c8360cc09a5a75412075ff3f156f854614f7a86))


### Bug Fixes

* **deps:** update dependency mypy to v1.16.1 ([#286](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/286)) ([10e59e1](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/10e59e1b12e5a0dc58f9724a55aca8ed057c0ea2))
* **deps:** update dependency pytest to v8.4.1 ([#288](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/288)) ([4237fff](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/4237fffddf18a274fda6a23f16354a0199da9506))
* **deps:** update python-nonmajor ([#289](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/289), [#284](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/284)) ([2725fd2](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/2725fd2bc82150e1f6b4bc3df16dec9e29e4f83a), [492d35f](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/492d35f61360494e60944f8f5939cc23dabca80f))
* **toolbox-core:** Expose authorization token requirements on `ToolboxTool` ([#294](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/294)) ([d7c3311](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/d7c3311db18eb2785a4c5dc89233a91fc222d84d))


### Documentation

* Add complete e2e working quickstart link across all quickstart sections ([#296](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/296)) ([b839bc5](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/b839bc5acd10142888739c2abaff215a32eb3e62))

## [0.2.1](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-core-v0.2.0...toolbox-core-v0.2.1) (2025-06-13)


### Features

* Cache google id tokens ([#254](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/254)) ([4e832c8](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/4e832c8aa89f65f183f2cb13d55440292b1dc09d))


### Bug Fixes

* allow auth token getter override over client header ([#283](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/283)) ([c2d6cd6](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/c2d6cd66673e81e2b4cc3a43b4a897a3a04723f0))
* **deps:** update dependency pytest-asyncio to v1 ([#261](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/261)) ([9400621](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/94006211658fa5852e2a7e17497ec30e157cdc3e))
* **deps:** update python-nonmajor ([#257](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/257)) ([79005ad](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/79005ada9960dc593eb116289a93175032a9ee1a))
* **deps:** update python-nonmajor ([#266](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/266)) ([fecbf3d](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/fecbf3d58647aec670b2cf7bad929d4605ad2cc8))
* **deps:** update python-nonmajor ([#274](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/274)) ([35ee427](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/35ee427443311a896f98b9e8f57187f6d502e3d7))
* **deps:** update python-nonmajor ([#282](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/282)) ([a58cc11](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/a58cc113d59b2e5f08460225a4d894dda0ca3e0c))
* **toolbox-core:** Prevent `ToolboxClient` from closing externally managed client sessions ([#260](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/260)) ([7520adf](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/7520adf8f75b2d8d9d254cfa43774ba876fcd222))


### Miscellaneous Chores

* **deps:** update dependency aiohttp to v3.12.12 ([#276](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/276)) ([c69e029](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/c69e0296b8f3ef792c1d56be0bd66194d0bf5710))
* **deps:** update dependency aiohttp to v3.12.9 ([#272](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/272)) ([813d60e](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/813d60e40f036faa2bf7d1c72457ceb39c1c37d1))
* **toolbox-core:** deprecate add_headers feature ([#278](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/278)) ([65c8b10](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/65c8b101f28476935aa677a4223cccc775af9cf1))
* Update Gemini model to a stable version ([#263](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/263)) ([3661055](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/36610558b205b72de7e40c469cdaabb5a715c4a3))
* Update tools file option in integration tests ([#277](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/277)) ([cf1d0ab](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/cf1d0ab145b067a8cc817eeacd7aa05ba3a6990f))


### Documentation

* Improve API error handling for `toolbox-core` client ([#275](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/275)) ([65398fd](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/65398fd0c98c95188304670651a84d002e11d030))
* **toolbox-core:** Update README to include guidance on session lifecycle management ([#259](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/259)) ([9997fb6](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/9997fb6b5cc1195b6732ecba3823309951a3e096))

## [0.2.0](https://github.com/googleapis/mcp-toolbox-sdk-python/compare/toolbox-core-v0.1.0...toolbox-core-v0.2.0) (2025-05-20)


### ⚠ BREAKING CHANGES

* **toolbox-core:** Throw PermissionError on unauthenticated tool invocation ([#233](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/233))
* **toolbox-core:** Simplify add_headers to make it sync in async client ([#231](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/231))
* **toolbox-core:** Standardize on ValueError for improved error consistency ([#219](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/219))
* **toolbox-core:** Rename bind_parameters to bind_params ([#209](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/209))

### Features

* Add bind_param (singular) to align with other packages ([#210](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/210)) ([a2810c1](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/a2810c198a52a43a52d2e95f1cd09ab8409d912f))
* Add client headers to Toolbox ([#178](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/178)) ([e73f6b6](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/e73f6b607219d1d51304dde21f7d9c0bf24fc915))
* Add convenience methods for adding single auth token getter to tools ([#245](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/245)) ([44b0697](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/44b0697efd693db364c0b8cf8b9dfa929e428ef6))
* Allow loading default toolset (all tools) ([#153](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/153)) ([0f3b4eb](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/0f3b4ebb55d5d4fafecf7ceb648460784b76c257))
* **core:** Add client_headers to ToolboxSyncClient ([#187](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/187)) ([50e32da](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/50e32da6bed00c7bcba194406dcc4e0387f452f2))
* Enhance authorization token validation with authRequired ([#222](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/222)) ([2dad7c8](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/2dad7c8422e420f2f10a68f0ebbeaca4aa26a5e1))
* Implement strict validation for client while loading tools ([#205](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/205)) ([c7eebbb](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/c7eebbb42ff24c77936cdac6b6d2b685ef282a64))
* Introduce identifying used authz token getters ([#221](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/221)) ([5d49936](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/5d4993622dd3a05b26710c7325c827cb7575913b))
* Introduce Tracking of Used Auth and Bound Keys in parse_tool for Client Strictness ([#184](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/184)) ([edd1f3a](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/edd1f3ad9d63ef2db2adf93f1373a8b51d5c6b20))
* Make name optional while loading toolset through sync client ([#235](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/235)) ([9527824](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/9527824b92232a0b7644015f64c7438086d0596a))
* **toolbox_core:** add helper methods for retrieving ID tokens ([#239](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/239)) ([b3213cc](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/b3213cc9eaeb7052cefdee7e7ee81efab080b2c6))
* **toolbox-core:** Rename bind_parameters to bind_params ([#209](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/209)) ([a36ae42](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/a36ae42532fbcb8ad114c14dc9017b5b0b81e589))
* **toolbox-langchain:** Base toolbox-langchain over toolbox-core ([#229](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/229)) ([03d1b16](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/03d1b160db602f7aeb1c25bc77014ff440ea7504))
* Track utilized auth services ([#203](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/203)) ([527369c](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/527369c3b1b2b475a26619081207b92ed4c1b6ba))
* Warn on insecure tool invocation with authentication ([#223](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/223)) ([d331e3c](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/d331e3c7b424cb3b16122321a7e82a4e6712a6a2))


### Bug Fixes

* Add validation to ensure added auth token getters are used by the tool ([#220](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/220)) ([7cde398](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/7cde39878b94d29940be2b69bd12b6c9d927ad81))
* **deps:** update python-nonmajor ([#175](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/175)) ([73e5a4a](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/73e5a4ac63ee39486529952351c06179ee268c7c))
* **deps:** update python-nonmajor ([#180](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/180)) ([8d909a9](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/8d909a9e19abed4a02e30a4dfc48e06afdbb01ea))
* Ensure `__parse_tool` returns correct `used_auth_keys` ([#204](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/204)) ([d0b5020](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/d0b5020dceca76feffa66f64d91237d284b9bcfb))
* Fix issue causing masking of empty loop or thread check while loading tool/toolset ([#227](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/227)) ([a4f0f25](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/a4f0f25ce6dd6ee09f08e0340bc92f5a21527f9d))
* **toolbox-core:** Add strict flag support to sync client ([#230](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/230)) ([4e19a3c](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/4e19a3cea7a13821b1c13404944a6b892308cfd0))
* **toolbox-core:** Prevent rebinding of parameters in ToolboxTool ([#186](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/186)) ([906d0e0](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/906d0e080e553e963c2ebfb15c94bf3efdd4886c))
* **toolbox-core:** Simplify add_headers to make it sync in async client ([#231](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/231)) ([394fa4d](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/394fa4d20436b2ca1fc8b9fa84654aa0be4cd6f4))
* **toolbox-core:** Standardize on ValueError for improved error consistency ([#219](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/219)) ([cdfaaf8](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/cdfaaf871e8225510aa4a8892fc186bd528e8472))
* **toolbox-core:** Throw PermissionError on unauthenticated tool invocation ([#233](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/233)) ([7dbf087](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/7dbf08743d2d2d4df35cab690379ba5e72d82f32))


### Miscellaneous Chores

* Add unit tests for the tool, client and protocol files ([#170](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/170)) ([14bc4ee](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/14bc4eec7c85329c6a41d1cd21e7eccbe68b0a7c))
* Add unit tests for ToolboxSyncClient ([#225](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/225)) ([3516be5](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/3516be521250f7ed097da1a280bf970f9e48e756))
* Add unit tests for ToolboxSyncTool ([#224](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/224)) ([787ba5d](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/787ba5d869cc59ca4e3eaec5944a0d2be319473d))
* correct import in readme ([#154](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/154)) ([2825581](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/2825581c105189bea2ccb31beaf50001512f9a49))
* Delint + minor simplification of import statement ([#185](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/185)) ([6693407](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/6693407421e94bc7a02be62e257ce33d9f75a34f))
* **deps:** update dependency pydantic to v2.11.3 ([#163](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/163)) ([6a78495](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/6a78495ecfe8b51992f55518ab0e7dca1bd6f849))
* **deps:** update dependency pydantic to v2.11.4 ([#200](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/200)) ([758f620](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/758f620e25427396b52d257722d7f71312421ad1))
* fix supported python versions ([#191](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/191)) ([f308b5f](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/f308b5f7d7019635798000d0921cf3f549075fd8))
* Make type hints of tool and client classes more accurate and specific ([#249](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/249)) ([996545e](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/996545e1f66a547a416b2eefcfd7cbcf73abd320))
* rebrand as MCP Toolbox ([#156](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/156)) ([d090a3f](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/d090a3f2af35a2e3e1e5d59b3176b026af510b7b))
* remove unused fixtures ([#212](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/212)) ([34a573c](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/34a573ceebba7737eed42bf5d91dbf45f2f8784f))
* remove unused fixtures ([#216](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/216)) ([0ff650a](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/0ff650a1d96ea3355b2cd707573c093d985557c6))
* Remove unused variable ([#171](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/171)) ([bddc8b5](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/bddc8b52886732eb3cdec936cb8c58f27ac829e6))
* rename repo ([#165](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/165)) ([70a476a](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/70a476a4fed46a905fe77101c3c1077fd6d5bd21))
* Simplify sync_client fixture ([#240](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/240)) ([75b79c9](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/75b79c9f625fe1944664304cab48b5cc22bf9693))
* **toolbox-core:** Add property decorators to tool ([#218](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/218)) ([b85820b](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/b85820b60bf9f7b237cf517ff83f954321a34258))
* **toolbox-core:** Consolidate auth header creation logic ([#213](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/213)) ([a10964f](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/a10964f41dc71934b88d0300e47fc4340da6ad3b))
* **toolbox-core:** Correctly name test file ([#214](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/214)) ([5d4a02e](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/5d4a02e61c2f3b04918b8fa52d8ae0aebc8ceb56))
* **toolbox-core:** Move util functions to a separate file in toolbox core ([#174](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/174)) ([ca88369](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/ca88369f5dd388299d32b9662443152c74397b3b))
* **toolbox-core:** Remove unused typevar variables ([#232](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/232)) ([aa69aab](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/aa69aab702ecdf5006081d4ca224b6b1a34c793f))
* update toolbox version ([#188](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/188)) ([58d8f7d](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/58d8f7d4601495faf2a33a48cc26bb0a599622ed))
* update toolbox version ([#190](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/190)) ([87e21ed](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/87e21ed07035ec96fb7b6c730585061d17d727c7))
* update toolbox version ([#226](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/226)) ([2a92def](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/2a92def08825417b32faa523a3355eba34351955))


### Documentation

* fix grammar ([#179](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/179)) ([afebaa6](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/afebaa6bfcb2e855823c64a56f4f249da2a721d7))
* Fix variable name in helper docstring ([#183](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/183)) ([eb5856b](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/eb5856b047fbaeee1375c2e7a6135f2fcf2526c3))
* Update docstring for strict flag to make it unambiguous ([#247](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/247)) ([59f0634](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/59f063446b98965c1fa8818d8ab93d5cd5d0b2ec))
* Update docstring to be more accurate ([#199](https://github.com/googleapis/mcp-toolbox-sdk-python/issues/199)) ([d055723](https://github.com/googleapis/mcp-toolbox-sdk-python/commit/d0557237bd6f936d52d79c66606e3d7fd2ef0afd))

## 0.1.0 (2025-04-04)


### Features

* **toolbox-core:** add type validation to params when tool is invoked ([#129](https://github.com/googleapis/genai-toolbox-langchain-python/issues/129)) ([5d62138](https://github.com/googleapis/genai-toolbox-langchain-python/commit/5d621388b3dc8d6fb7583b56dc9d7fcfa02c0a8b))
* **toolbox-core:** Added a sync toolbox client ([#131](https://github.com/googleapis/genai-toolbox-langchain-python/issues/131)) ([ed82832](https://github.com/googleapis/genai-toolbox-langchain-python/commit/ed82832b6e84e8e278820b537fbdbfabd1a0b250))
* **toolbox-core:** add authenticated parameters support ([#119](https://github.com/googleapis/genai-toolbox-langchain-python/issues/119)) ([10087a1](https://github.com/googleapis/genai-toolbox-langchain-python/commit/10087a136056cd47765b376ba18897bae5b848a3))
* **toolbox-core:** add support for bound parameters ([#120](https://github.com/googleapis/genai-toolbox-langchain-python/issues/120)) ([b2a2208](https://github.com/googleapis/genai-toolbox-langchain-python/commit/b2a22089d4a9abc067605d603c077ff4c4843147))
* **toolbox-core:** updated generated docstring to include parameters and their descriptions ([#127](https://github.com/googleapis/genai-toolbox-langchain-python/issues/127)) ([eafe2e9](https://github.com/googleapis/genai-toolbox-langchain-python/commit/eafe2e9cb1e2f84e3b2ba5bee5c469ae5754ade9))
* **toolbox-core:** add basic implementation  ([#103](https://github.com/googleapis/genai-toolbox-langchain-python/issues/103)) ([4f992d8](https://github.com/googleapis/genai-toolbox-langchain-python/commit/4f992d8b2d3cc75692d030b67d13f90c36c49ac9))

### Documentation
* **toolbox-core:** add README ([#132](https://github.com/googleapis/genai-toolbox-langchain-python/issues/132)) ([839ed94](https://github.com/googleapis/genai-toolbox-langchain-python/commit/839ed940b5d8de31a83a98b375a7fd24402f5267))


### Bug Fixes

* **toolbox-core:** Add qualname for ToolboxTool instances ([#134](https://github.com/googleapis/genai-toolbox-langchain-python/issues/134)) ([5c2dff7](https://github.com/googleapis/genai-toolbox-langchain-python/commit/5c2dff7b2378eaa9298cc281b3658f85a32aa1a5))
* **toolbox-core:** correct invalid reference when using array types ([#128](https://github.com/googleapis/genai-toolbox-langchain-python/issues/128)) ([d5a3259](https://github.com/googleapis/genai-toolbox-langchain-python/commit/d5a325926e3fb03b33f9133e7cc70fa935b9aecb))
