from sqlalchemy import ForeignKey, Table, Column, Integer
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING, Type, Optional, Literal


def ForeignKeyField(
    to_model: str,
    on_delete: str = "CASCADE",
    nullable: bool = True,
    index: bool = True,
) -> Column:
    return Column(
        Integer,
        ForeignKey(f"{to_model}.id", ondelete=on_delete),
        nullable=nullable,
        index=index,
    )


def OneToMany(
    to_model: str,
    back_populates: Optional[str] = None,
    lazy: Literal["select", "joined", "selectin", "subquery", "raise", "raise_on_sql"] = "selectin",
):
    return relationship(
        to_model,
        back_populates=back_populates,
        lazy=lazy,
        cascade="all, delete-orphan",
    )


def ManyToOne(
    to_model: str,
    back_populates: Optional[str] = None,
    lazy: Literal["select", "joined", "selectin", "subquery", "raise", "raise_on_sql"] = "selectin",
):
    return relationship(to_model, back_populates=back_populates, lazy=lazy)


def ManyToMany(
    to_model: str,
    secondary: Table,
    back_populates: Optional[str] = None,
    lazy: Literal["select", "joined", "selectin", "subquery", "raise", "raise_on_sql"] = "selectin",
):
    return relationship(
        to_model,
        secondary=secondary,
        back_populates=back_populates,
        lazy=lazy,
    )


def create_association_table(table_name: str, left_table: str, right_table: str, base):
    return Table(
        table_name,
        base.metadata,
        Column("id", Integer, primary_key=True),
        Column(
            f"{left_table}_id",
            Integer,
            ForeignKey(f"{left_table}.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column(
            f"{right_table}_id",
            Integer,
            ForeignKey(f"{right_table}.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
