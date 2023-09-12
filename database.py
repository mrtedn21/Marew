from datetime import date
from typing import Callable

from pydantic import ConfigDict, create_model
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from openapi import add_openapi_schema


class Base(AsyncAttrs, DeclarativeBase):
    pass


class SqlAlchemyToPydantic(type(Base)):
    """Metaclass that get sql alchemy model fields, creates pydantic
    model based on them and moreover, metaclass extends schemas of
    openapi object with models it creates.

    Example:
    -------
    class NewModel(SomeSqlAlchemyModel, metaclass=SqlAlchemyToPydantic):
        fields = '__all__'

    fields attribute can be on of:
    * '__all__' - means that pydantic model will be with all
        fields of alchemy model
    * '__without_pk__' - means will be all fields instead of pk
    * tuple[str] - is tuple of fields that will be used
    """

    def __new__(cls, name, bases, fields):
        origin_model = bases[0]

        origin_model_field_names = [
            field_name for field_name in dir(origin_model)
            if not field_name.startswith('_') and field_name not in
            ('registry', 'metadata', 'awaitable_attrs') and not cls.is_second_relation(origin_model, field_name)
        ]

        defined_fields = fields['fields']
        if defined_fields == '__all__':
            defined_fields = origin_model_field_names
        elif defined_fields == '__without_pk__':
            defined_fields = tuple(set(origin_model_field_names) - {'pk'})

        result_fields = {
            field_name:
                (getattr(origin_model, field_name).type.python_type, ...)
            for field_name in defined_fields
            if field_name in origin_model_field_names
        }
        result_model = create_model(
            name,
            **result_fields,
            __config__=ConfigDict(from_attributes=True),
        )
        add_openapi_schema(name, result_model)
        return result_model

    @staticmethod
    def is_second_relation(model, attribute_name):
        attribute = getattr(model, attribute_name)

        try:
            collection_class = attribute.prop.collection_class
        except AttributeError:
            return False

        if collection_class is not None:
            return True
        else:
            return False


class UserOrm(Base):
    __tablename__ = 'users'

    pk: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    birth_date: Mapped[date]
    city: Mapped['CityOrm'] = relationship(back_populates='users')


class CityOrm(Base):
    __tablename__ = 'cities'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped['CountryOrm'] = relationship(back_populates='cities')
    users: Mapped[list['UserOrm']] = relationship(back_populates='city')


class CountryOrm(Base):
    __tablename__ = 'countries'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    cities: Mapped[list['CityOrm']] = relationship(back_populates='country')


class DataBase:
    def __init__(self):
        self.engine: AsyncEngine = create_async_engine(
            'postgresql+asyncpg://alexander.bezgin:123@localhost/framework',
            echo=True,
        )
        self.create_session: Callable = async_sessionmaker(self.engine)
