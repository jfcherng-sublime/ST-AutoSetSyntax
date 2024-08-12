from magika.types.strenum import StrEnum as StrEnum

class Status(StrEnum):
    OK = 'ok'
    FILE_NOT_FOUND_ERROR = 'file_not_found_error'
    PERMISSION_ERROR = 'permission_error'
    UNKNOWN = 'unknown'
