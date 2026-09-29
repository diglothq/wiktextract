"""Output models for the Norwegian Wiktionary edition."""

from pydantic import BaseModel, ConfigDict, Field


class NorwegianBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
        validate_default=True,
    )


class FormOf(NorwegianBaseModel):
    word: str


class Sense(NorwegianBaseModel):
    glosses: list[str] = []
    form_of: list[FormOf] = []
    tags: list[str] = []
    raw_tags: list[str] = []


class Translation(NorwegianBaseModel):
    lang_code: str
    lang: str = ""
    word: str
    sense: str = ""


class Form(NorwegianBaseModel):
    form: str
    tags: list[str] = []


class WordEntry(NorwegianBaseModel):
    model_config = ConfigDict(
        title="Norwegian Wiktionary", **NorwegianBaseModel.model_config
    )

    word: str = Field(description="Page title")
    lang_code: str = Field(description="Language code of this entry")
    lang: str = Field(description="Language name in Norwegian")
    pos: str = Field(description="Normalized part of speech")
    pos_title: str = ""
    senses: list[Sense] = []
    forms: list[Form] = []
    translations: list[Translation] = []
    tags: list[str] = []
