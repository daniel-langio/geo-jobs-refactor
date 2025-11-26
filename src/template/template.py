from typing import Dict

class Template:
    def __init__(self, name: str, blueprint: str):
        self.name = name
        self.blueprint = blueprint

    def build(self, params: Dict[str, str]) -> str:
        return Template.build_template(self.blueprint, params)

    def build_template(template: str, params: Dict[str, str]) -> str:
        try:
            return template.format(**params)
        except KeyError as e:
            raise ValueError(f"Error while building template:\nMissing parameter: {e.args[0]}")
