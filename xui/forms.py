"""Validation de formulaires XUI par Pydantic.

Pas d'injection automatique FastAPI (`Annotated[Model, Form()]`) : sur
échec, son comportement par défaut est un 422 JSON — inutilisable pour une
page HTML, où on veut ré-afficher le même template avec un message par
champ et les valeurs déjà saisies conservées. `parse_form()` valide donc
explicitement dans la route (toujours une route FastAPI ordinaire, §6/§15 —
seule la validation change), et renvoie un `FormResult` prêt à repasser tel
quel au contexte de rendu (`errors`, `values`).
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError
from starlette.datastructures import FormData

ModelT = TypeVar("ModelT", bound=BaseModel)


class FormResult(Generic[ModelT]):
    def __init__(self, data: ModelT | None, errors: dict[str, str], values: dict[str, str]) -> None:
        self.data = data
        self.errors = errors
        self.values = values

    @property
    def ok(self) -> bool:
        return self.data is not None


def parse_form(form: FormData, model: type[ModelT]) -> FormResult[ModelT]:
    """Valide les champs d'un `FormData` Starlette contre un modèle Pydantic.

    Toujours des chaînes en entrée (un `<form>` HTML n'envoie que du texte) —
    Pydantic se charge de la coercition (int, bool, EmailStr, etc.) et du
    message d'erreur par champ en cas d'échec.
    """
    values = {k: v for k, v in form.items() if isinstance(v, str)}
    try:
        return FormResult(data=model(**values), errors={}, values=values)
    except ValidationError as exc:
        errors: dict[str, str] = {}
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"]) or "__root__"
            errors[field] = err["msg"]
        return FormResult(data=None, errors=errors, values=values)
