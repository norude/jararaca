from abc import ABC
from dataclasses import dataclass, field
from typing import Callable
from sys import stderr
import sys
from .type import Type
from . import type as types 
from .core import NEWLINE, get_id
from .token import TT, Loc, Token
class Node(ABC):
	pass
@dataclass(slots=True, frozen=True)
class Tops(Node):
	tops:'list[Node]'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{NEWLINE.join([str(i) for i in self.tops])}"
@dataclass(slots=True, frozen=True)
class FunctionCall(Node):
	name:Token
	args:'list[Node|Token]'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.name}({', '.join([str(i) for i in self.args])})"
@dataclass(slots=True, frozen=True)
class TypedVariable(Node):
	name:Token
	typ:'Type'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.name}: {self.typ}"
@dataclass(slots=True, frozen=True)
class ExprStatement(Node):
	value:'Node | Token'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.value}"
@dataclass(slots=True, frozen=True)
class Assignment(Node):
	var:'TypedVariable'
	value:'Node|Token'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.var} = {self.value}"
@dataclass(slots=True, frozen=True)
class ReAssignment(Node):
	name:'Token'
	value:'Node|Token'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.name} = {self.value}"
@dataclass(slots=True, frozen=True)
class Defining(Node):
	var:'TypedVariable'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.var}"
@dataclass(slots=True, frozen=True)
class ReferTo(Node):
	name:Token
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.name}"
@dataclass(slots=True, frozen=True)
class IntrinsicConstant(Node):
	name:Token
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.name}"
	@property
	def typ(self) -> 'Type':
		if   self.name.operand == 'False': return types.BOOL
		elif self.name.operand == 'True' : return types.BOOL
		else:
			assert False, f"Unreachable, unknown {self.name=}"
@dataclass(slots=True, frozen=True)
class BinaryExpression(Node):
	left:'Token | Node'
	operation:Token
	right:'Token | Node'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"({self.left} {self.operation} {self.right})"
	def typ(self,left:Type,right:Type) -> 'Type':
		op = self.operation
		lr = left, right
		if   op == TT.PLUS                  and lr == (types.INT, types.INT): return types.INT
		elif op == TT.PLUS                  and lr == (types.PTR, types.INT): return types.PTR
		elif op == TT.MINUS                 and lr == (types.INT, types.INT): return types.INT
		elif op == TT.ASTERISK              and lr == (types.INT, types.INT): return types.INT
		elif op == TT.DOUBLE_SLASH          and lr == (types.INT, types.INT): return types.INT
		elif op == TT.PERCENT_SIGN          and lr == (types.INT, types.INT): return types.INT
		elif op == TT.LESS_SIGN             and lr == (types.INT, types.INT): return types.BOOL
		elif op == TT.GREATER_SIGN          and lr == (types.INT, types.INT): return types.BOOL
		elif op == TT.DOUBLE_LESS_SIGN      and lr == (types.INT, types.INT): return types.INT
		elif op == TT.DOUBLE_GREATER_SIGN   and lr == (types.INT, types.INT): return types.INT
		elif op == TT.DOUBLE_EQUALS_SIGN    and lr == (types.INT, types.INT): return types.BOOL
		elif op == TT.NOT_EQUALS_SIGN       and lr == (types.INT, types.INT): return types.BOOL
		elif op == TT.LESS_OR_EQUAL_SIGN    and lr == (types.INT, types.INT): return types.BOOL
		elif op == TT.GREATER_OR_EQUAL_SIGN and lr == (types.INT, types.INT): return types.BOOL
		elif op.equals(TT.KEYWORD, 'or' ) and lr == (types.BOOL, types.BOOL): return types.BOOL
		elif op.equals(TT.KEYWORD, 'xor') and lr == (types.BOOL, types.BOOL): return types.BOOL
		elif op.equals(TT.KEYWORD, 'and') and lr == (types.BOOL, types.BOOL): return types.BOOL
		elif op.equals(TT.KEYWORD, 'or' ) and lr == (types.INT,  types.INT ): return types.INT
		elif op.equals(TT.KEYWORD, 'xor') and lr == (types.INT,  types.INT ): return types.INT
		elif op.equals(TT.KEYWORD, 'and') and lr == (types.INT,  types.INT ): return types.INT
		else:
			print(f"ERROR: {self.operation.loc}: unsupported operation '{self.operation}' for '{left}' and '{right}'", file=stderr)
			sys.exit(47)
@dataclass(slots=True, frozen=True)
class UnaryExpression(Node):
	operation:Token
	left:'Token | Node'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"({self.operation} {self.left})"
	def typ(self,left:Type) -> 'Type':
		op = self.operation
		l = left
		if op == TT.NOT and l == types.BOOL: return types.BOOL
		if op == TT.NOT and l == types.INT : return types.INT
		else:
			print(f"ERROR: {self.operation.loc}: unsupported operation '{self.operation}' for '{left}'", file=stderr)
			sys.exit(48)
@dataclass(slots=True, frozen=True)
class Dot(Node):
	origin:'Node|Token'
	access:'Token'
	loc:'Loc'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.origin}.{self.access}"
	def lookup_struct(self,struct:'Struct') -> 'tuple[int, Type]':
		for idx,var in enumerate(struct.variables):
			if var.name == self.access:
				return idx,var.typ
		print(f"ERROR: {self.access.loc} did not found field {self.access} of struct {self.origin}", file=stderr)
		sys.exit(49)
@dataclass(slots=True, frozen=True)
class GetItem(Node):
	origin:'Node|Token'
	idx:'Node|Token'
	loc:'Loc'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"{self.origin}[{self.idx}]"
@dataclass(slots=True, frozen=True)
class Fun(Node):
	name:Token
	arg_types:'list[TypedVariable]'
	output_type:'Type'
	code:"Code"
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		prefix = f""
		if len(self.arg_types) > 0:
			return f"{prefix}fun {self.name} {' '.join([str(i) for i in self.arg_types])} -> {self.output_type} {self.code}"
		return f"{prefix}fun {self.name} -> {self.output_type} {self.code}"
@dataclass(slots=True, frozen=True)
class Memo(Node):
	name:'Token'
	size:int
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"memo {self.name} {self.size}"
@dataclass(slots=True, frozen=True)
class Var(Node):
	name:'Token'
	typ:Type
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"var {self.name} {self.typ}"
@dataclass(slots=True, frozen=True)
class Const(Node):
	name:'Token'
	value:int
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"const {self.name} {self.value}"
@dataclass(slots=True, frozen=True)
class Code(Node):
	statements:'list[Node | Token]'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		tab:Callable[[str], str] = lambda s: s.replace('\n', '\n\t')
		return f"{{{tab(NEWLINE+NEWLINE.join([str(i) for i in self.statements]))}{NEWLINE}}}"
@dataclass(slots=True, frozen=True)
class If(Node):
	loc:Loc
	condition:'Node|Token'
	code:'Node'
	else_code:'Node|None' = None
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		if self.else_code is None:
			return f"if {self.condition} {self.code}"
		if isinstance(self.else_code, If):
			return f"if {self.condition} {self.code} el{self.else_code}"

		return f"if {self.condition} {self.code} else {self.else_code}"

@dataclass(slots=True, frozen=True)
class Return(Node):
	loc:Loc
	value:'Node|Token'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"return {self.value}"
@dataclass(slots=True, frozen=True)
class While(Node):
	loc:Loc
	condition:'Node|Token'
	code:'Code'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"while {self.condition} {self.code}"
@dataclass(slots=True, frozen=True)
class Struct(Node):
	loc:Loc
	name:Token
	variables:'list[TypedVariable]'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		tab:Callable[[str], str] = lambda s: s.replace('\n', '\n\t')
		return f"struct {self.name} {{{tab(NEWLINE+NEWLINE.join([str(i) for i in self.variables]))}{NEWLINE}}}"
	@property
	def sizeof(self) -> int:
		return 8*sum(int(var.typ) for var in self.variables)
@dataclass(slots=True, frozen=True)
class Cast(Node):
	loc:Loc
	typ:Type
	value:'Node|Token'
	uid:int = field(default_factory=get_id, compare=False, repr=False)
	def __str__(self) -> str:
		return f"${self.typ}({self.value})"