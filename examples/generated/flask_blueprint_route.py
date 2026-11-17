# -*- coding: utf-8 -*-
# 由 ai-bigdata-rag 生成：检索增强（RAG），语料来自 GitHub 公共仓库。
# 生成时间：2026-11-17T22:39:14+08:00
# 检索模式：extractive；命中片段：5；词项覆盖率：100%
# 问题：Flask Blueprint 如何注册路由？
# 引用来源：
#   - [pallets/flask:src/flask/sansio/app.py:555-587]  ->  pallets/flask/src/flask/sansio/app.py
#   - [pallets/flask:src/flask/sansio/blueprints.py:247-272]  ->  pallets/flask/src/flask/sansio/blueprints.py
#   - [pallets/flask:src/flask/sansio/app.py:580-604]  ->  pallets/flask/src/flask/sansio/app.py
#   - [pallets/flask:src/flask/sansio/blueprints.py:265-295]  ->  pallets/flask/src/flask/sansio/blueprints.py
#   - [pallets/flask:src/flask/app.py:1188-1213]  ->  pallets/flask/src/flask/app.py
# 语法检查：通过（ast.parse）
# 注意：生成代码需人工复核后再用于生产；许可证遵循上游仓库。
@debug.setter
def debug(self, value: bool) -> None:
    self.config["DEBUG"] = value

    if self.config["TEMPLATES_AUTO_RELOAD"] is None:
        self.jinja_env.auto_reload = value


def make_setup_state(
    self, app: App, options: dict[str, t.Any], first_registration: bool = False
) -> BlueprintSetupState:
    """Creates an instance of :meth:`~flask.blueprints.BlueprintSetupState`
    object that is later passed to the register callback functions.
    Subclasses can override this to return a subclass of the setup state.
    """
    return BlueprintSetupState(self, app, options, first_registration)
