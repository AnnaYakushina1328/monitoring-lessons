def is_admin(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.role == "admin"
        )
    )


def is_methodist(user):
    return (
        user.is_authenticated
        and user.role == "methodist"
    )


def is_expert(user):
    return (
        user.is_authenticated
        and user.role == "expert"
    )


def can_create_visit(user):
    """
    Планировать посещения может
    администратор / superuser.
    """
    return is_admin(user)


def can_view_visit(user, visit):
    """
    Администратор и методист видят все посещения.
    Эксперт — только те, куда он назначен.
    """

    if is_admin(user) or is_methodist(user):
        return True

    if is_expert(user):
        return visit.auditors.filter(
            pk=user.pk
        ).exists()

    return False


def can_edit_assessment(user, visit):
    """
    Методист имеет только просмотр.

    Заполнять чек-лист могут:
    - администратор;
    - назначенный эксперт.
    """

    if is_admin(user):
        return True

    if is_expert(user):
        return visit.auditors.filter(
            pk=user.pk
        ).exists()

    return False


def visible_visits_for(user):
    """
    Возвращает только те посещения,
    которые пользователь имеет право видеть.
    """

    from visits.models import Visit

    queryset = Visit.objects.all()

    if (
        is_admin(user)
        or is_methodist(user)
    ):
        return queryset

    if is_expert(user):
        return queryset.filter(
            auditors=user
        ).distinct()

    return queryset.none()
