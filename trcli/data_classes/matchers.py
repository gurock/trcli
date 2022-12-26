class Matchers:

    AUTO = "auto"
    NAME = "name"
    PROPERTY = "property"

    @staticmethod
    def parse_name_with_id(case_name: str) -> (str, str):
        if case_name.lower().startswith("[c"):
            close_idx = case_name.find("]")
            case_id = int(case_name[2:close_idx])
            case_name = case_name[close_idx + 1:].lstrip()
            return case_id, case_name
        else:
            return None, case_name
