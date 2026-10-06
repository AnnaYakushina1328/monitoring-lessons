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
    Администратор и методист могут
    планировать и администрировать посещения.
    """

    return (
        is_admin(user)
        or is_methodist(user)
    )


def can_view_visit(user, visit):
    """
    Администратор и методист видят
    все посещения.

    Эксперт видит только те посещения,
    куда он назначен.
    """

    if (
        is_admin(user)
        or is_methodist(user)
    ):
        return True

    if is_expert(user):
        return visit.auditors.filter(
            pk=user.pk
        ).exists()

    return False


def can_edit_assessment(user, visit):
    """
    Заполнять чек-лист могут:

    - администратор;
    - методист, назначенный на посещение;
    - эксперт, назначенный на посещение.
    """

    if is_admin(user):
        return True


    if is_methodist(user):

        return visit.methodists.filter(
            pk=user.pk
        ).exists()


    if is_expert(user):

        return visit.auditors.filter(
            pk=user.pk
        ).exists()


    return False


def visible_visits_for(user):
    """
    Администратор и методист видят все
    посещения.

    Эксперт видит только назначенные ему.
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



def can_view_monitoring(user):
    """
    Сводный мониторинг доступен:
    - администратору;
    - методисту.
    """

    return (
        is_admin(user)
        or is_methodist(user)
    )
