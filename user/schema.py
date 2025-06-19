import graphene
from graphene_django import DjangoObjectType

from user.models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude = ("password",)


class Query(graphene.ObjectType):
    all_users = graphene.List(UserType)
    user_by_id = graphene.Field(UserType, id=graphene.UUID(required=True))

    def resolve_all_users(self, info, **kwargs):
        return User.objects.filter(is_deleted=False, is_staff=True, is_superuser=False)

    def resolve_user_by_id(self, info, id):
        return User.objects.get(id=id)
