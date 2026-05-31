from contextvars import ContextVar

_request_state: ContextVar[dict | None] = ContextVar("request_state", default=None)


def bind_request_state() -> None:
    _request_state.set({"access_services": {}, "reporting_tree": None})


def clear_request_state() -> None:
    _request_state.set(None)


def get_request_state() -> dict | None:
    return _request_state.get()


def get_request_access_service(user):
    from apps.customers.services.access import CustomerAccessService

    state = get_request_state()
    if state is None:
        return CustomerAccessService(user)

    services = state["access_services"]
    key = str(user.pk)
    if key not in services:
        services[key] = CustomerAccessService(user)
    return services[key]
