from .permissions import is_manager, is_support


def navigation(request):
    return {"support_member": is_support(request.user), "desk_manager": is_manager(request.user)}
