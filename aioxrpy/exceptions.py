from aioxrpy.definitions import RippleTransactionResultCategory


class RippleBaseException(Exception):
    def __init__(self, error, payload={}):
        self.payload = payload
        self.error = error


class RippleTransactionException(RippleBaseException):
    def __init__(self, error, category, payload={}):
        super().__init__(error, payload)
        self.category = category


class RippleTransactionCostlyFailureException(RippleTransactionException):
    def __init__(self, error, payload={}):
        super().__init__(
            error, RippleTransactionResultCategory.CostlyFailure, payload
        )


class RippleTransactionLocalFailureException(RippleTransactionException):
    def __init__(self, error, payload={}):
        super().__init__(
            error, RippleTransactionResultCategory.LocalFailure, payload
        )


class RippleTransactionMalformedException(RippleTransactionException):
    def __init__(self, error, payload={}):
        super().__init__(
            error, RippleTransactionResultCategory.MalformedFailure, payload
        )


class RippleTransactionRetriableException(RippleTransactionException):
    def __init__(self, error, payload={}):
        super().__init__(
            error, RippleTransactionResultCategory.RetriableFailure, payload
        )


class RippleTransactionFailureException(RippleTransactionException):
    def __init__(self, error, payload={}):
        super().__init__(
            error, RippleTransactionResultCategory.Failure, payload
        )


class RippleSerializerUnsupportedTypeException(RippleBaseException):
    def __init__(self, payload={}):
        super().__init__('serializer_unsupported_type', payload)


class UnknownRippleException(RippleBaseException):
    def __init__(self, payload={}):
        super().__init__('unknown_error', payload)


class InvalidTransactionException(RippleBaseException):
    def __init__(self, payload={}):
        super().__init__('invalid_transaction', payload)


class AccountNotFoundException(RippleBaseException):
    def __init__(self, payload={}):
        super().__init__('act_not_found', payload)
