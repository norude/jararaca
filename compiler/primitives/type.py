from enum import Enum as pythons_enum, auto
from dataclasses import dataclass
__all__ = [
	'Type',
]
class Type:
	def __str__(self) -> str:
		raise TypeError("Method is abstract")
	def __repr__(self) -> str:
		return str(self)
	@property
	def llvm(self) -> str:
		raise TypeError("Method is abstract")
	@property
	def sized(self) -> bool:
		raise TypeError("Method is abstract")
class Primitive(Type,pythons_enum):
	INT   = auto()
	STR   = auto()
	BOOL  = auto()
	VOID  = auto()
	CHAR  = auto()
	SHORT = auto()
	def __str__(self) -> str:
		return self.name.lower()
	@property
	def llvm(self) -> str:
		table:dict[Type, str] = {
			Primitive.VOID : 'void',
			Primitive.INT  : 'i64',
			Primitive.SHORT: 'i32',
			Primitive.CHAR : 'i8',
			Primitive.BOOL : 'i1',
			Primitive.STR  : '%str.type',
		}
		return table[self]
	@property
	def sized(self) -> bool:
		return self != VOID

INT   = Primitive.INT
BOOL  = Primitive.BOOL
STR   = Primitive.STR
VOID  = Primitive.VOID
CHAR  = Primitive.CHAR
SHORT = Primitive.SHORT
@dataclass(slots=True, frozen=True)
class Ptr(Type):
	pointed:Type
	def __str__(self) -> str:
		return f"*{self.pointed}"
	@property
	def llvm(self) -> str:
		p = self.pointed.llvm
		if p == 'ptr':
			return "ptr"
		if p == 'void':
			return 'i8*'
		return f"{p}*"
	@property
	def sized(self) -> bool:
		return True
PTR = Ptr(VOID)
@dataclass()#no slots or frozen to simulate a pointer
class Struct(Type):#modifying is allowed only to create recursive data
	name:str
	variables:tuple[tuple[str,Type],...]
	struct_uid:int
	funs:'tuple[tuple[str,Fun,str],...]'
	def __str__(self) -> str:
		return self.name
	def get_magic(self, magic:'str') -> 'tuple[Fun,str]|None':
		for name,fun,llvmid in self.funs:
			if name == f'__{magic}__':
				return fun,llvmid
		return None
	@property
	def llvm(self) -> str:
		return f"%\"struct.{self.struct_uid}.{self.name}\""
	def is_sized(self) -> bool:
		return all(var.sized for _,var in self.variables)
	_is_sizing:bool = False
	@property
	def sized(self) -> bool:
		if self._is_sizing:
			return False
		self._is_sizing = True
		ret = self.is_sized()
		self._is_sizing = False
		return ret
	def __hash__(self) -> int:
		return hash((
			self.name,
			self.struct_uid
		))
@dataclass(slots=True, frozen=True)
class Fun(Type):
	all_arg_types:tuple[Type, ...]
	bound_args:int
	return_type:Type
	@property
	def arg_types(self) -> tuple[Type, ...]:
		return self.all_arg_types[self.bound_args:]
	def __str__(self) -> str:
		return f"({', '.join(f'{arg}' for arg in self.arg_types)}) -> {self.return_type}"
	@property
	def llvm(self) -> str:
		return f"{{ {self.fun_llvm}, {PTR.llvm} }}"
	@property
	def fun_llvm(self) -> str:
		return f"{self.return_type.llvm} ({', '.join((PTR.llvm,*(arg.llvm for arg in self.arg_types)))})*"
	@property
	def sized(self) -> bool:
		return True


@dataclass(slots=True, frozen=True)
class Module(Type):
	module_uid:'int'
	path:'str'
	def __str__(self) -> str:
		return f"#module({self.path})"
	@property
	def llvm(self) -> str:
		assert False, "Module type is not saveable"
	@property
	def sized(self) -> bool:
		return False
@dataclass(slots=True, frozen=True)
class Mix(Type):
	funs:tuple[Type, ...]
	name:str
	def __str__(self) -> str:
		return f"#mix({self.name})"
	@property
	def llvm(self) -> str:
		return f"{{{', '.join(i.llvm for i in self.funs)}}}"
	@property
	def sized(self) -> bool:
		return True

@dataclass(slots=True, unsafe_hash=True)
class Array(Type):
	typ:Type
	size:int = 0
	def __str__(self) -> str:
		if self.size == 0:
			return f"[]{self.typ}"
		return f"[{self.size}]{self.typ}"
	@property
	def llvm(self) -> str:
		return f"[{self.size} x {self.typ.llvm}]"
	def is_sized(self) -> bool:
		if self.size == 0:
			return False
		return self.typ.sized
	_is_sizing:bool = False
	@property
	def sized(self) -> bool:
		if self._is_sizing:
			return False
		self._is_sizing = True
		ret = self.is_sized()
		self._is_sizing = False
		return ret
@dataclass(slots=True, unsafe_hash=True)
class StructKind(Type):
	statics:tuple[tuple[str,Type], ...]
	struct:'Struct'
	@property
	def name(self) -> str:
		return self.struct.name
	@property
	def struct_uid(self) -> int:
		return self.struct.struct_uid
	def __str__(self) -> str:
		return f"#structkind({self.name})"
	@property
	def llvm(self) -> str:
		return f"%\"structkind.{self.struct_uid}.{self.name}\""
	@property
	def llvmid(self) -> str:
		return f"@__structkind.{self.struct_uid}.{self.name}"
	def is_sized(self) -> bool:
		return all(var.sized for _,var in self.statics)
	_is_sizing:bool = False
	@property
	def sized(self) -> bool:
		if self._is_sizing:
			return False
		self._is_sizing = True
		ret = self.is_sized()
		self._is_sizing = False
		return ret


@dataclass()#no slots or frozen to simulate a pointer
class Enum(Type):#modifying is allowed only to create recursive data
	name:str
	items:tuple[str,...]
	typed_items:tuple[tuple[str,Type],...]
	funs:'tuple[tuple[str,Fun,str],...]'
	enum_uid:int
	def get_magic(self, magic:'str') -> 'tuple[Fun,str]|None':
		for name,fun,llvmid in self.funs:
			if name == f'__{magic}__':
				return fun,llvmid
		return None
	@property
	def llvm(self) -> str:
		return f"%\"enum.{self.enum_uid}.{self.name}\""
	@property
	def llvm_max_item(self) -> str:
		return f"%\"enum.max_item.{self.enum_uid}.{self.name}\""
	@property
	def llvm_item_id(self) -> str:
		return f"%\"enum.item_id.{self.enum_uid}.{self.name}\""
	def __str__(self) -> str:
		return self.name
	def is_sized(self) -> bool:
		return all(var.sized for _,var in self.typed_items)
	_is_sizing:bool = False
	@property
	def sized(self) -> bool:
		if self._is_sizing:
			return False
		self._is_sizing = True
		ret = self.is_sized()
		self._is_sizing = False
		return ret
	def __hash__(self) -> int:
		return hash((
			self.enum_uid,
			self.name,
			self.items,
		))

@dataclass(slots=True, frozen=True)
class EnumKind(Type):
	enum:'Enum'
	@property
	def name(self) -> str:
		return self.enum.name
	@property
	def enum_uid(self) -> int:
		return self.enum.enum_uid
	def __str__(self) -> str:
		return f"#enum_kind({self.name})"
	@property
	def llvm(self) -> str:
		assert False, f"enum kind is not saveable"
	def llvmid_of_type_function(self, idx:int) -> str:
		return f"@\"__enum.{self.enum_uid}.{self.name}.fun_to_create_enum_no.{idx}.{self.enum.typed_items[idx][0]}\""
	@property
	def sized(self) -> bool:
		return False
