class ValidationException(Exception):
    """Exception raised for validation errors in dataclass.

    Attributes:
        field_name: input field name that didn't pass validation
        class_name: input class name that didn't pass validation
        reason: reason of validation error
    """

    def __init__(self, field_name: str, class_name: str, reason=""):
        self.field_name = field_name
        self.class_name = class_name
        self.reason = reason
        super().__init__(f"Unable to parse {field_name} in {class_name} property. {reason}")
