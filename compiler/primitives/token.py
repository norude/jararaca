from dataclasses import dataclass, field
from enum import Enum, auto
from .core import Config, Place, escape, Loc, ET
__all__ = [
	'Token',
	'TT',
]
@dataclass(slots=True, frozen=True, order=True)
class draft_loc:
	file_path:str
	file_text:str = field(compare=False, repr=False)
	config:Config
	idx:int       = 0
	rows:int      = field(default=1, compare=False, repr=False)
	cols:int      = field(default=1, compare=False, repr=False)
	def __add__(self, number:int) -> 'draft_loc':
		idx, cols, rows = self.idx, self.cols, self.rows
		if idx+number>=len(self.file_text):
			self.config.errors.critical_error(ET.EOF, Place(self.to_loc(),self.to_loc()), "unexpected end of file while lexing")
		for _ in range(number):
			idx+=1
			cols+=1
			if self.file_text[idx-1] =='\n':
				cols = 1
				rows+= 1
		return self.__class__(self.file_path, self.file_text, self.config, idx, rows, cols)
	def __str__(self) -> str:
		return f"{self.file_path}:{self.rows}:{self.cols}"

	@property
	def char(self) -> str:
		return self.file_text[self.idx]
	def __bool__(self) -> bool:
		return self.idx < len(self.file_text)-1

	def to_loc(self) -> Loc:
		return Loc(
			file_path= self.file_path,
			idx      = self.idx,
			line     = self.rows,
			cols     = self.cols,
		)
class TT(Enum):
	SHORT                 = auto()
	INT                   = auto()
	CHAR                  = auto()
	WORD                  = auto()
	KEYWORD               = auto()
	STR                   = auto()
	TEMPLATE_HEAD         = auto()
	TEMPLATE_MIDDLE       = auto()
	TEMPLATE_TAIL         = auto()
	NO_MIDDLE_TEMPLATE    = auto()
	LEFT_CURLY_BRACKET    = auto()
	RIGHT_CURLY_BRACKET   = auto()
	LEFT_SQUARE_BRACKET   = auto()
	RIGHT_SQUARE_BRACKET  = auto()
	LEFT_PARENTHESIS      = auto()
	RIGHT_PARENTHESIS     = auto()
	EOF                   = auto()
	ARROW                 = auto()
	NEWLINE               = auto()
	COLON                 = auto()
	COMMA                 = auto()
	EQUALS                = auto()
	AT                    = auto()
	NOT                   = auto()
	DOT                   = auto()
	NOT_EQUALS            = auto()
	DOUBLE_EQUALS         = auto()
	GREATER               = auto()
	GREATER_OR_EQUAL      = auto()
	LESS                  = auto()
	LESS_OR_EQUAL         = auto()
	DOUBLE_LESS           = auto()
	DOUBLE_GREATER        = auto()
	PLUS                  = auto()
	MINUS                 = auto()
	ASTERISK              = auto()
	DOUBLE_SLASH          = auto()
	PERCENT               = auto()
	DOLLAR                = auto()
	def __str__(self) -> str:
		names = {
			TT.GREATER:'>',
			TT.LESS:'<',
			TT.DOUBLE_GREATER:'>>',
			TT.DOUBLE_LESS:'<<',
			TT.LESS_OR_EQUAL:'<=',
			TT.GREATER_OR_EQUAL:'>=',
			TT.DOUBLE_EQUALS:'==',
			TT.NOT:'!',
			TT.AT:'@',
			TT.NOT_EQUALS:'!=',
			TT.PLUS:'+',
			TT.MINUS:'-',
			TT.ASTERISK:'*',
			TT.DOUBLE_SLASH:'//',
			TT.PERCENT:'%',
			TT.NEWLINE:'\n',
			TT.ARROW:'->',
		}
		return names.get(self, self.name.lower())
@dataclass(slots=True, frozen=True, eq=False)
class Token:
	place:Place = field(compare=False)
	typ:TT
	operand:str = ''
	def __str__(self) -> str:
		if self.typ == TT.STR:
			return f'"{escape(self.operand)}"'
		if self.typ == TT.CHAR:
			return f'{ord(self.operand)}c'
		if self.operand != '':
			return escape(self.operand)
		return escape(str(self.typ))
	def equals(self, typ_or_token:'TT|Token', operand:str|None = None) -> bool:
		if isinstance(typ_or_token, Token):
			operand = typ_or_token.operand
			typ_or_token = typ_or_token.typ
			return self.typ == typ_or_token and self.operand == operand
		if operand is None:
			return self.typ == typ_or_token
		return self.typ == typ_or_token and self.operand == operand

	def __eq__(self, other: object) -> bool:
		if not isinstance(other, (TT, Token)):
			return NotImplemented
		return self.equals(other)

	def __hash__(self) -> int:
		return hash((self.typ, self.operand))
