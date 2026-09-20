from pydantic import BaseModel, ConfigDict, EmailStr


class CustomerBase(BaseModel):
    name: str
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    is_active: bool | None = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
