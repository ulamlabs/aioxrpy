class RippleBaseException(Exception):
    pass


class RippleUnfundedPaymentException(RippleBaseException):
    error = 'unfunded_payment'


class RippleSerializerUnsupportedTypeException(RippleBaseException):
    error = 'serializer_unsupported_type'


class UnknownRippleError(RippleBaseException):
    error = 'unknown_error'


class DestinationDoesntExistError(RippleBaseException):
    error = 'no_dst'


class NotEnoughAmountToCreateDestinationError(DestinationDoesntExistError):
    error = 'no_dst_insuf_xrp'


class NeedMasterKeyError(RippleBaseException):
    error = 'need_master_key'


class InsufficientReserveError(RippleBaseException):
    error = 'insufficient_reserve'


class InsufficientReserveOfferError(InsufficientReserveError):
    error = 'insufficient_reserve_offer'


class InsufficientReserveLineError(InsufficientReserveError):
    error = 'insufficient_reserve_line'


class AssetsFrozenError(RippleBaseException):
    error = 'frozen'


class BadAmountError(RippleBaseException):
    error = 'bad_amount'


class BadFeeError(RippleBaseException):
    error = 'bad_fee'


class AccountNotFoundError(RippleBaseException):
    error = 'act_not_found'


class ValidatedLedgerUnavailable(RippleBaseException):
    # Custom error for when validated_ledger field is missing
    error = 'validated_ledger_unavailable'


def ripple_error_to_exception(error):
    return {
        'actNotFound': AccountNotFoundError
    }.get(
        error,
        UnknownRippleError({'error': error})
    )


def ripple_result_to_exception(category, code):
    """
    https://xrpl.org/tec-codes.html
    """
    return {
        'UNFUNDED_PAYMENT': RippleUnfundedPaymentException,
        'NO_DST': DestinationDoesntExistError,
        'NO_DST_INSUF_XRP': NotEnoughAmountToCreateDestinationError,
        'NEED_MASTER_KEY': NeedMasterKeyError,
        'INSUFFICIENT_RESERVE': InsufficientReserveError,
        'INSUFFICIENT_RESERVE_OFFER': InsufficientReserveOfferError,
        'INSUFFICIENT_RESERVE_LINE': InsufficientReserveLineError,
        'FROZEN': AssetsFrozenError,
        'BAD_AMOUNT': BadAmountError,
        'BAD_FEE': BadFeeError,
    }.get(
        code,
        UnknownRippleError(
            data={
                'category': category,
                'code': code
            }
        )
    )
