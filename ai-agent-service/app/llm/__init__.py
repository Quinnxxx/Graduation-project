"""LLM 工厂包。

集中管理大模型客户端（对话 / Embedding）的创建，统一从 :class:`Settings`
读取模型、平台与密钥配置，禁止在业务代码中硬编码任何模型参数或密钥。

各 Agent 通过 :meth:`LLMFactory.create_chat_llm` 按需创建对话模型实例，
后期替换模型只需修改 ``.env``，零代码改动。
"""
