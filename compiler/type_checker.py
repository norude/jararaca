from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from .primitives import nodes, Node, ET, Config, Type, types, DEFAULT_TEMPLATE_STRING_FORMATTER, BUILTIN_WORDS, Place
__all__ = (
	'SemanticTokenType',
	'SemanticTokenModifier',
	'SemanticToken',
	'TypeChecker',
)
class SemanticTokenType(Enum):
	MODULE           = auto()
	STRUCT           = auto()
	ARGUMENT         = auto()
	VARIABLE         = auto()
	PROPERTY         = auto()
	FUNCTION         = auto()
	BOUND_FUNCTION   = auto()
	MIX              = auto()
	STRING           = auto()
	INTEGER          = auto()
	CHARACTER_STRING = auto()
	CHARACTER_NUMBER = auto()
	SHORT            = auto()
	OPERATOR         = auto()
	TYPE             = auto()
	ENUM 		     = auto()
	ENUM_ITEM        = auto()
	def __str__(self) -> str:
		return self.name.lower().replace('_', ' ')
class SemanticTokenModifier(Enum):
	DECLARATION  = auto()
	DEFINITION   = auto()
	STATIC       = auto()
	def __str__(self) -> str:
		return self.name.lower()
@dataclass(frozen=True, slots=True)
class SemanticToken:
	place:Place
	typ:SemanticTokenType
	modifiers:tuple[SemanticTokenModifier,...] = ()
	value_type:Type|None = None
	def_place:Place|None = None

expand:Callable[
[tuple[Type,Place]|None],
tuple[Type,Place]|tuple[None,None]] = lambda x:(None,None) if x is None else (x[0],x[1])

imported_modules:'dict[str,TypeChecker]' = {}

class TypeChecker:
	__slots__ = ('config', 'module', 'modules', 'names', 'type_names', 'expected_return_type', 'semantic', 'semantic_tokens')
	def __init__(self, module:nodes.Module, config:Config, semantic:bool = False) -> None:
		self.module = module
		self.config = config
		self.names:dict[str, tuple[Type,Place]] = {}#regular definitions like `var x int`
		self.type_names:dict[str, tuple[Type,Place]] = {}#type definitions like `struct X {}`
		self.modules:dict[int, TypeChecker] = {}
		self.expected_return_type:Type = types.VOID
		self.semantic:bool = semantic
		if self.semantic:
			self.semantic_tokens:set[SemanticToken] = set()
	def go_check(self) -> None:
		if self.module.builtin_module is not None:
			tc = self.import_module(self.module.builtin_module)
			for name in BUILTIN_WORDS:
				type_definition = tc.type_names.get(name)
				definition = tc.names.get(name)
				assert type_definition is not None or None is not definition, f"Unreachable, std.builtin does not have word '{name}' defined, but it must"
				if definition is not None:
					self.names[name] = definition
				if type_definition is not None:
					self.type_names[name] = type_definition
		for top in self.module.tops:
			self.check(top)

	def import_module(self,module:nodes.Module) -> 'TypeChecker':
		if module.path in imported_modules:
			tc = imported_modules[module.path]
		else:
			tc = TypeChecker(module, self.config)
			tc.go_check()
			imported_modules[module.path] = tc
		self.modules[module.uid] = tc
		return tc

	def check_import(self, node:nodes.Import) -> Type:
		self.import_module(node.module)
		self.names[node.name] = types.Module(node.module.uid,node.module.path),node.path_place
		if self.semantic:self.semantic_tokens.add(SemanticToken(node.path_place, SemanticTokenType.MODULE, (SemanticTokenModifier.DECLARATION,)))
		return types.VOID
	def check_from_import(self, node:nodes.FromImport) -> Type:
		tc = self.import_module(node.module)
		for nam in node.imported_names:
			name = nam.operand
			type_definition = tc.type_names.get(name)
			definition = tc.names.get(name)
			if type_definition is definition is None:
				self.config.errors.add_error(ET.IMPORT_NAME, node.place, f"name '{name}' is not defined in module '{node.module.path}'")
			if self.semantic:
				self.semantic_reference_helper_from_typ(definition, nam.place, (SemanticTokenModifier.DECLARATION,))
			if definition is not None:
				self.names[name] = definition
			if type_definition is not None:
				self.type_names[name] = type_definition
		if self.semantic:self.semantic_tokens.add(SemanticToken(node.path_place, SemanticTokenType.MODULE, (SemanticTokenModifier.DECLARATION,)))
		return types.VOID
	def check_enum(self, node:nodes.Enum) -> Type:
		enum_type = types.Enum('',(),(),(),0)
		self.type_names[node.name.operand] = enum_type,node.name.place
		actual_enum_type = node.to_enum(self.check)
		enum_type.__dict__ = actual_enum_type.__dict__#FIXME
		del actual_enum_type
		self.names[node.name.operand] = node.to_enum_kind(self.check),node.name.place
		if self.semantic:self.semantic_tokens.add(SemanticToken(node.name.place, SemanticTokenType.ENUM, (SemanticTokenModifier.DEFINITION,)))
		for fun in node.funs:
			rt = self.check(fun.return_type) if fun.return_type is not None else types.VOID
			self.check_bound_fun_helper(types.Ptr(node.to_enum(self.check)),fun,rt)
		if self.semantic:
			for item in node.items:
				self.semantic_tokens.add(SemanticToken(item.place, SemanticTokenType.ENUM_ITEM, (SemanticTokenModifier.DEFINITION,)))
			for typed_item in node.typed_items:
				self.semantic_tokens.add(SemanticToken(typed_item.name.place, SemanticTokenType.ENUM_ITEM, (SemanticTokenModifier.DEFINITION,), self.check(typed_item.typ)))
		return types.VOID
	def check_fun(self, node:nodes.Fun, semantic_type:SemanticTokenType = SemanticTokenType.FUNCTION, bound_args:int=0, add_name:bool=True) -> Type:
		if add_name and bound_args==0:
			self.names[node.name.operand] = node.typ(self.check,bound_args),node.name.place
		if node.is_main:
			if node.return_type is not None:
				if self.check(node.return_type) != types.VOID:
					self.config.errors.add_error(ET.MAIN_RETURN, node.return_type_place, f"entry point (function 'main') has to return {types.VOID}, found '{node.return_type}'")
			if len(node.arg_types) != 0:
				self.config.errors.add_error(ET.MAIN_ARGS, node.args_place, f"entry point (function 'main') has to take no arguments, found '({', '.join(map(str,node.arg_types))})'")
		vars_before = self.names.copy()
		self.names.update({arg.name.operand:(self.check(arg.typ),arg.name.place) for arg in node.arg_types})
		ert_before = self.expected_return_type
		self.expected_return_type = self.check(node.return_type) if node.return_type is not None else types.VOID
		actual_ret_typ = self.check(node.code)
		specified_ret_typ = self.check(node.return_type) if node.return_type is not None else types.VOID
		if specified_ret_typ != actual_ret_typ:
			self.config.errors.add_error(ET.FUN_RETURN, node.return_type_place, f"specified return type is '{specified_ret_typ}' but function did not return")
		self.names = vars_before
		self.expected_return_type = ert_before
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.name.place,semantic_type,(SemanticTokenModifier.DEFINITION,), node.typ(self.check,bound_args)))
			for arg in node.arg_types:
				self.semantic_tokens.add(SemanticToken(arg.name.place,SemanticTokenType.ARGUMENT,(SemanticTokenModifier.DECLARATION,)))
		return types.VOID
	def check_code(self, node:nodes.Code) -> Type:
		vars_before = self.names.copy()
		ret:Type = types.VOID
		for statement in node.statements:
			#every statement's check should return types.VOID if (and only if) there is a way, that `return` can be not executed in it
			r = self.check(statement)
			#... should return self.expected_return_type if (and only if) `return` will be definitely executed it this statement
			if ret == types.VOID != r:
				ret = r
				assert r == self.expected_return_type, f"{type(statement)} statement did not follow return rules"
				#other things are not allowed
		self.names = vars_before #this is scoping
		return ret
	def check_call(self, node:nodes.Call) -> Type:
		return self.call_helper(self.check(node.func), [self.check(arg) for arg in node.args], node.place)
	def call_helper(self, function:Type, args:list[Type], place:Place) -> Type:
		def get_fun_out_of_called(called:Type) -> types.Fun:
			if isinstance(called, types.Fun):
				return called
			if isinstance(called, types.StructKind):
				m = called.struct.get_magic('init')
				if m is None:
					self.config.errors.critical_error(ET.INIT_MAGIC, place, f"structure '{called}' has no '__init__' magic defined")
				magic,_ = m
				return types.Fun(
					magic.all_arg_types,
					1,
					types.Ptr(called.struct)
				)
			if isinstance(called, types.Mix):
				for ref in called.funs:
					fun = get_fun_out_of_called(ref)
					if len(args) != len(fun.arg_types):
						continue#continue searching
					for actual_arg,arg in zip(args,fun.arg_types,strict=True):
						if actual_arg != arg:
							break#break to continue
					else:
						return fun#found fun
					continue
				self.config.errors.critical_error(ET.CALL_MIX, place, f"did not find function to match '{','.join(map(str,args))}' contract in mix '{called.name}'")
			self.config.errors.critical_error(ET.CALLABLE, place, f"'{called}' object is not callable")
		fun = get_fun_out_of_called(function)
		if len(fun.arg_types) != len(args):
			self.config.errors.critical_error(ET.CALL_ARGS, place, f"function '{fun}' accepts {len(fun.arg_types)} arguments, provided {len(args)} arguments")
		for idx, typ in enumerate(args):
			needed = fun.arg_types[idx]
			if typ != needed:
				self.config.errors.add_error(ET.CALL_ARG, place, f"function '{fun}' argument {idx} takes '{needed}', got '{typ}'")
		return fun.return_type
	def check_bin_exp(self, node:nodes.BinaryOperation) -> Type:
		left = self.check(node.left)
		right = self.check(node.right)
		result = node.typ(left,right, self.config)
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.operation.place,SemanticTokenType.OPERATOR,value_type=result))
		return result
	def check_expr_state(self, node:nodes.ExprStatement) -> Type:
		self.check(node.value)
		return types.VOID
	def check_str(self, node:nodes.Str) -> Type:
		result = types.STR
		if self.semantic:self.semantic_tokens.add(SemanticToken(node.place,SemanticTokenType.STRING,value_type=result))
		return result
	def check_int(self, node:nodes.Int) -> Type:
		result = types.INT
		if self.semantic:self.semantic_tokens.add(SemanticToken(node.place,SemanticTokenType.INTEGER,value_type=result))
		return result
	def check_short(self, node:nodes.Short) -> Type:
		result = types.SHORT
		if self.semantic:self.semantic_tokens.add(SemanticToken(node.place,SemanticTokenType.SHORT,value_type=result))
		return result
	def check_char_str(self, node:nodes.CharStr) -> Type:
		result = types.CHAR
		if self.semantic:self.semantic_tokens.add(SemanticToken(node.place,SemanticTokenType.CHARACTER_STRING,value_type=result))
		return result
	def check_char_num(self, node:nodes.CharNum) -> Type:
		result = types.CHAR
		if self.semantic:self.semantic_tokens.add(SemanticToken(node.place,SemanticTokenType.CHARACTER_NUMBER,value_type=result))
		return result
	def check_assignment(self, node:nodes.Assignment) -> Type:
		actual_type = self.check(node.value)
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.var.name.place,SemanticTokenType.VARIABLE, (SemanticTokenModifier.DEFINITION,),actual_type))
		if self.check(node.var.typ) != actual_type:
			self.config.errors.add_error(ET.ASSIGNMENT, node.place, f"specified type '{node.var.typ}' does not match actual type '{actual_type}' in assignment")
		self.names[node.var.name.operand] = types.Ptr(self.check(node.var.typ)),node.var.name.place
		return types.VOID
	def semantic_reference_helper_from_typ(self, definition:tuple[Type,Place]|None, place:Place, modifiers:tuple[SemanticTokenModifier, ...] = ()) -> None:
		typ, def_place = expand(definition)
		if self.semantic:
			if   isinstance(typ, types.Struct)    :self.semantic_tokens.add(SemanticToken(place,SemanticTokenType.STRUCT,                                                               modifiers, typ, def_place))
			elif isinstance(typ, types.Fun)       :self.semantic_tokens.add(SemanticToken(place,SemanticTokenType.FUNCTION if typ.bound_args == 0 else SemanticTokenType.BOUND_FUNCTION,modifiers, typ, def_place))
			elif isinstance(typ, types.Mix)       :self.semantic_tokens.add(SemanticToken(place,SemanticTokenType.MIX,                                                                  modifiers, typ, def_place))
			elif isinstance(typ, types.Module)    :self.semantic_tokens.add(SemanticToken(place,SemanticTokenType.MODULE,                                                               modifiers, typ, def_place))
			else                                  :self.semantic_tokens.add(SemanticToken(place,SemanticTokenType.VARIABLE,                                                             modifiers, typ, def_place))
	def check_refer(self, node:nodes.ReferTo) -> Type:
		typ = self.names.get(node.name.operand)
		if self.semantic:
			self.semantic_reference_helper_from_typ(typ, node.name.place)
		if typ is None:
			self.config.errors.critical_error(ET.REFER, node.place, f"did not find name '{node.name}'")
		return typ[0]
	def check_declaration(self, node:nodes.Declaration) -> Type:
		typ = self.check(node.var.typ)
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.var.name.place,SemanticTokenType.VARIABLE, (SemanticTokenModifier.DECLARATION,),typ))
		if not typ.sized:
			self.config.errors.add_error(ET.SIZED_DECLARATION, node.place, f"type '{typ}' is not sized, so it can't be declared")
		if node.times is None:
			self.names[node.var.name.operand] = types.Ptr(typ), node.var.name.place
			return types.VOID
		times = self.check(node.times)
		if times != types.INT:
			self.config.errors.add_error(ET.DECLARATION_TIMES, node.place, f"number of elements to allocate should be an '{types.INT}', got '{times}'")
		self.names[node.var.name.operand] = types.Ptr(types.Array(typ)),node.var.name.place
		return types.VOID
	def check_save(self, node:nodes.Save) -> Type:
		space = self.check(node.space)
		value = self.check(node.value)
		if not isinstance(space, types.Ptr):
			self.config.errors.critical_error(ET.SAVE_PTR, node.place, f"expected pointer to save into, got '{space}'")
		if space.pointed != value:
			self.config.errors.add_error(ET.SAVE, node.place, f"space type '{space}' does not match value's type '{value}'")
		return types.VOID
	def check_variable_save(self, node:nodes.VariableSave) -> Type:
		space,_ = expand(self.names.get(node.space.operand))
		value = self.check(node.value)
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.space.place,SemanticTokenType.VARIABLE, (SemanticTokenModifier.DEFINITION,),value))
		if space is None:#auto
			space = types.Ptr(value)
			self.names[node.space.operand] = space,node.space.place
		if not space.sized:
			self.config.errors.add_error(ET.SIZED_VSAVE, node.place, f"type '{value}' is not sized, so it can't be saved")
		if not isinstance(space, types.Ptr):
			self.config.errors.critical_error(ET.VSAVE_PTR, node.place, f"expected pointer to save into, got '{space}'")
		if space.pointed != value:
			self.config.errors.add_error(ET.VSAVE, node.place, f"space type '{space}' does not match value's type '{value}'")
		return types.VOID
	def check_if(self, node:nodes.If) -> Type:
		actual = self.check(node.condition)
		if actual != types.BOOL:
			self.config.errors.add_error(ET.IF, node.condition.place, f"if statement expected '{types.BOOL}' type, got '{actual}'")
		if node.else_code is None:
			self.check(node.code)
			return types.VOID
		actual_if = self.check(node.code)
		actual_else = self.check(node.else_code)
		if actual_if != actual_else:
			self.config.errors.critical_error(ET.IF_BRANCH, node.place, f"if branches are inconsistent: one branch returns while other does not (refactor without 'else')")
		return actual_if
	def check_while(self, node:nodes.While) -> Type:
		actual = self.check(node.condition)
		if actual != types.BOOL:
			self.config.errors.add_error(ET.WHILE, node.place, f"while statement expected '{types.BOOL}' type, got '{actual}'")
		return self.check(node.code)
	def check_set(self, node:nodes.Set) -> Type:
		value = self.check(node.value)
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.name.place,SemanticTokenType.VARIABLE, (SemanticTokenModifier.DEFINITION,),value))
		self.names[node.name.operand] = value,node.name.place
		return types.VOID
	def check_unary_exp(self, node:nodes.UnaryExpression) -> Type:
		result = node.typ(self.check(node.left), self.config)
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.operation.place,SemanticTokenType.OPERATOR,value_type=result))
		return result
	def check_constant(self, node:nodes.Constant) -> Type:
		return node.typ
	def check_var(self, node:nodes.Var) -> Type:
		self.names[node.name.operand] = types.Ptr(self.check(node.typ)),node.name.place
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.name.place,SemanticTokenType.VARIABLE, (SemanticTokenModifier.DECLARATION,),self.check(node.typ)))
		return types.VOID
	def check_const(self, node:nodes.Const) -> Type:
		self.names[node.name.operand] = types.INT,node.name.place
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.name.place,SemanticTokenType.VARIABLE, (SemanticTokenModifier.DEFINITION,),types.INT))
		return types.VOID
	def check_struct(self, node:nodes.Struct) -> Type:
		struct_type = types.Struct('',(),0,())
		self.type_names[node.name.operand] = struct_type,node.name.place
		actual_struct_type = node.to_struct(self.check)
		struct_type.__dict__ = actual_struct_type.__dict__#FIXME
		del actual_struct_type
		self.names[node.name.operand] = node.to_struct_kind(self.check),node.name.place
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.name.place,SemanticTokenType.STRUCT, (SemanticTokenModifier.DEFINITION,),node.to_struct(self.check)))
			for var in node.variables:
				self.semantic_tokens.add(SemanticToken(var.name.place,SemanticTokenType.PROPERTY, (SemanticTokenModifier.DEFINITION,),self.check(var.typ)))
		for fun in node.funs:
			rt = self.check(fun.return_type) if fun.return_type is not None else types.VOID
			self.check_bound_fun_helper(types.Ptr(node.to_struct(self.check)),fun,rt)
			if fun.name.operand == '__init__':
				if rt != types.VOID:
					self.config.errors.critical_error(ET.INIT_MAGIC_RET, fun.return_type_place, f"'__init__' magic method should return '{types.VOID}', not '{fun.return_type}'")
		for static_var in node.static_variables:
			value = self.check(static_var.value)
			if self.semantic:
				self.semantic_tokens.add(SemanticToken(static_var.var.name.place,SemanticTokenType.VARIABLE, (SemanticTokenModifier.DEFINITION,SemanticTokenModifier.STATIC), value))
			if self.check(static_var.var.typ) != value:
				self.config.errors.add_error(ET.STRUCT_STATICS, static_var.place, f"static variable '{static_var.var.name.operand}' has type '{static_var.var.typ}' but is assigned a value of type '{value}'")
		return types.VOID
	def check_bound_fun_helper(self,self_should_be:Type,fun:nodes.Fun,rt:Type) -> None:
		if len(fun.arg_types)==0:
			self.config.errors.critical_error(ET.BOUND_FUN_ARGS, fun.args_place, f"bound function's argument 0 should be '{self_should_be}' (self), found 0 arguments")
		elif self.check(fun.arg_types[0].typ) != self_should_be:
			self.config.errors.add_error(ET.BOUND_FUN_ARG, fun.arg_types[0].place, f"bound function's argument 0 should be '{self_should_be}' (self) got '{fun.arg_types[0].typ}'")
		if fun.name == '__str__':
			if len(fun.arg_types) != 1:
				self.config.errors.critical_error(ET.BOUND_STR_MAGIC, fun.args_place, f"magic function '__str__' should have 1 argument, not {len(fun.arg_types)}")
			if rt != types.STR:
				self.config.errors.critical_error(ET.BOUND__STR__RET, fun.return_type_place, f"magic function '__str__' should return {types.STR}, not {fun.return_type}")
		self.check_fun(fun, SemanticTokenType.BOUND_FUNCTION,False)
	def check_mix(self, node:nodes.Mix) -> Type:
		self.names[node.name.operand] = types.Mix(tuple(self.check(fun_ref) for fun_ref in node.funs),node.name.operand),node.name.place
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.name.place,SemanticTokenType.FUNCTION, (SemanticTokenModifier.DEFINITION,)))
		return types.VOID
	def check_use(self, node:nodes.Use) -> Type:
		self.names[node.as_name.operand] = types.Fun(tuple(self.check(arg) for arg in node.arg_types),0,self.check(node.return_type)),node.name.place
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.name.place,SemanticTokenType.FUNCTION, (SemanticTokenModifier.DECLARATION,)))
			if node.as_name is not node.name:
				self.semantic_tokens.add(SemanticToken(node.as_name.place,SemanticTokenType.FUNCTION))
		return types.VOID
	def check_return(self, node:nodes.Return) -> Type:
		ret = self.check(node.value)
		if ret != self.expected_return_type:
			self.config.errors.critical_error(ET.RETURN, node.place, f"actual return type '{ret}' does not match specified return type '{self.expected_return_type}'")
		return ret
	def check_assert(self, node:nodes.Assert) -> Type:
		value = self.check(node.value)
		explanation = self.check(node.explanation)
		if value != types.BOOL:
			self.config.errors.critical_error(ET.ASSERT_VALUE, node.value.place, f"assert value type '{value}' should be '{types.BOOL}'")
		if explanation != types.STR:
			self.config.errors.critical_error(ET.ASSERT_EXPLANATION, node.explanation.place, f"assert explanation type '{explanation}' should be '{types.STR}'")
		return types.VOID
	def check_dot(self, node:nodes.Dot) -> Type:
		origin = self.check(node.origin)
		if isinstance(origin, types.Module):
			typ,place = expand(self.modules[origin.module_uid].names.get(node.access.operand))
			if self.semantic:
				self.semantic_tokens.add(SemanticToken(node.access.place,SemanticTokenType.PROPERTY, value_type=typ,def_place=place))
			if typ is None:
				self.config.errors.critical_error(ET.DOT_MODULE, node.access.place, f"name '{node.access}' was not found in module '{origin.path}'")
			return typ
		if isinstance(origin, types.StructKind):
			_, ty = node.lookup_struct_kind(origin, self.config)
			if self.semantic:
				self.semantic_tokens.add(SemanticToken(node.access.place,SemanticTokenType.PROPERTY, value_type=ty))
			return ty
		if isinstance(origin, types.EnumKind):
			_,typ = node.lookup_enum_kind(origin, self.config)
			if self.semantic:
				self.semantic_tokens.add(SemanticToken(node.access.place,SemanticTokenType.ENUM_ITEM, value_type=typ))
			return typ
		if isinstance(origin,types.Ptr):
			pointed = origin.pointed
			if isinstance(pointed, types.Struct):
				k = node.lookup_struct(pointed, self.config)
				if isinstance(k[0],int):
					typ = types.Ptr(k[1])
				else:
					typ = k[0]
			elif isinstance(pointed, types.Enum):
				fun,_ = node.lookup_enum(pointed, self.config)
				typ = fun
			else:
				self.config.errors.critical_error(ET.DOT, node.access.place, f"'{origin}' object doesn't have any attributes")#same
			if self.semantic:self.semantic_tokens.add(SemanticToken(node.access.place,SemanticTokenType.PROPERTY, value_type=typ))
			return typ
		self.config.errors.critical_error(ET.DOT, node.access.place, f"'{origin}' object doesn't have any attributes")#same
	def check_get_item(self, node:nodes.Subscript) -> Type:
		origin = self.check(node.origin)
		subscripts = [self.check(subscript) for subscript in node.subscripts]
		if origin == types.STR:
			if len(subscripts) != 1:
				self.config.errors.critical_error(ET.STR_SUBSCRIPT_LEN, node.access_place, f"string subscripts should have 1 argument, not {len(subscripts)}")
			if subscripts[0] != types.INT:
				self.config.errors.add_error(ET.STR_SUBSCRIPT, node.access_place, f"string subscript should be 1 '{types.INT}' not '{subscripts[0]}'")
			return types.CHAR
		if isinstance(origin,types.Ptr):
			pointed = origin.pointed
			if isinstance(pointed, types.Array):
				if len(subscripts) != 1:
					self.config.errors.critical_error(ET.ARRAY_SUBSCRIPT_LEN, node.access_place, f"array subscripts should have 1 argument, not {len(subscripts)}")
				if subscripts[0] != types.INT:
					self.config.errors.add_error(ET.ARRAY_SUBSCRIPT, node.access_place, f"array subscript should be '{types.INT}' not '{subscripts[0]}'")
				return types.Ptr(pointed.typ)
			if isinstance(pointed, types.Struct):
				fu = pointed.get_magic('subscript')
				if fu is None:
					self.config.errors.critical_error(ET.SUBSCRIPT_MAGIC, node.access_place, f"structure '{pointed.name}' does not have __subscript__ magic defined")
				fun,_ = fu
				if len(subscripts) != len(fun.arg_types):
					self.config.errors.critical_error(ET.STRUCT_SUB_LEN, node.access_place, f"'{pointed}' struct subscript should have {len(fun.arg_types)} arguments, not {len(subscripts)}")
				for idx, subscript in enumerate(subscripts):
					if fun.arg_types[idx] != subscript:
						self.config.errors.add_error(ET.STRUCT_SUBSCRIPT, node.access_place, f"invalid subscript argument {idx} '{subscript}' for '{pointed}', expected type '{fun.arg_types[idx]}''")
				return fun.return_type
		self.config.errors.critical_error(ET.SUBSCRIPT, node.access_place, f"'{origin}' object is not subscriptable")
	def check_template(self, node:nodes.Template) -> Type:
		for val in node.values:
			self.check(val)
		if node.formatter is None:
			formatter,_ = expand(self.names.get(DEFAULT_TEMPLATE_STRING_FORMATTER))
			assert formatter is not None, "DEFAULT_TEMPLATE_STRING_FORMATTER was not imported from sys.builtin"
		else:
			formatter = self.check(node.formatter)
		if not isinstance(formatter, types.Fun):
			assert node.formatter is not None, "DEFAULT_TEMPLATE_STRING_FORMATTER does not meet requirements to be a formatter"
			self.config.errors.critical_error(ET.TEMPLATE_FUN, node.formatter.place, f"template formatter should be a function, not '{formatter}'")
		if len(formatter.arg_types) != 3:
			assert node.formatter is not None, "DEFAULT_TEMPLATE_STRING_FORMATTER does not meet requirements to be a formatter"
			self.config.errors.critical_error(ET.TEMPLATE_ARGS, node.formatter.place, f"template formatter should have 3 arguments, not {len(formatter.arg_types)}")
		if formatter.arg_types[0] != types.Ptr(types.Array(types.STR)):#*[]str
			assert node.formatter is not None, "DEFAULT_TEMPLATE_STRING_FORMATTER does not meet requirements to be a formatter"
			self.config.errors.add_error(ET.TEMPLATE_ARG0, node.formatter.place, f"template formatter argument 0 (strings) should be '{types.Ptr(types.Array(types.STR))}', not '{formatter.arg_types[0]}'")
		if formatter.arg_types[1] != types.Ptr(types.Array(types.STR)):#*[]str
			assert node.formatter is not None, "DEFAULT_TEMPLATE_STRING_FORMATTER does not meet requirements to be a formatter"
			self.config.errors.add_error(ET.TEMPLATE_ARG1, node.formatter.place, f"template formatter argument 1 (values) should be '{types.Ptr(types.Array(types.STR))}', not '{formatter.arg_types[1]}'")
		if formatter.arg_types[2] != types.INT:#int
			assert node.formatter is not None, "DEFAULT_TEMPLATE_STRING_FORMATTER does not meet requirements to be a formatter"
			self.config.errors.add_error(ET.TEMPLATE_ARG2, node.formatter.place, f"template formatter argument 2 (length) should be '{types.INT}', not '{formatter.arg_types[2]}'")
		return formatter.return_type
	def check_string_cast(self, node:nodes.StrCast) -> Type:
		# length should be int, pointer should be ptr(*[]char)
		length = self.check(node.length)
		if length != types.INT:
			self.config.errors.add_error(ET.STR_CAST_LEN, node.place, f"string length should be '{types.INT}' not '{length}'")
		pointer = self.check(node.pointer)
		if pointer != types.Ptr(types.Array(types.CHAR)):
			self.config.errors.add_error(ET.STR_CAST_PTR, node.place, f"string pointer should be '{types.Ptr(types.Array(types.CHAR))}' not '{pointer}'")
		return types.STR
	def check_cast(self, node:nodes.Cast) -> Type:
		left = self.check(node.value)
		right = self.check(node.typ)
		isptr:Callable[[Type], bool] = lambda typ: isinstance(typ, types.Ptr)
		if not (
			(isptr(left) and isptr(right)) or
			(left == types.STR   and right == types.Ptr(types.Array(types.CHAR))) or
			(left == types.STR   and right == types.INT  ) or
			(left == types.BOOL  and right == types.CHAR ) or
			(left == types.BOOL  and right == types.SHORT) or
			(left == types.BOOL  and right == types.INT  ) or
			(left == types.CHAR  and right == types.SHORT) or
			(left == types.CHAR  and right == types.INT  ) or
			(left == types.SHORT and right == types.INT  ) or
			(left == types.INT   and right == types.SHORT) or
			(left == types.INT   and right == types.CHAR ) or
			(left == types.INT   and right == types.BOOL ) or
			(left == types.SHORT and right == types.CHAR ) or
			(left == types.SHORT and right == types.BOOL ) or
			(left == types.CHAR  and right == types.BOOL )
		):
			self.config.errors.critical_error(ET.CAST, node.place, f"casting type '{left}' to type '{right}' is not supported")
		return right
	def check_type_pointer(self, node:nodes.TypePointer) -> Type:
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.place, SemanticTokenType.TYPE))
		pointed = self.check(node.pointed)
		return types.Ptr(pointed)
	def check_type_array(self, node:nodes.TypeArray) -> Type:
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.place, SemanticTokenType.TYPE))
		element = self.check(node.typ)
		return types.Array(element, node.size)
	def check_type_fun(self, node:nodes.TypeFun) -> Type:
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.place, SemanticTokenType.TYPE))
		args = tuple(self.check(arg) for arg in node.args)
		return_type:Type = types.VOID
		if node.return_type is not None:
			return_type = self.check(node.return_type)
		return types.Fun(args,0,return_type)
	def check_type_reference(self, node:nodes.TypeReference) -> Type:
		name = node.ref.operand
		if name == 'void': return types.VOID
		if name == 'bool': return types.BOOL
		if name == 'char': return types.CHAR
		if name == 'short': return types.SHORT
		if name == 'int': return types.INT
		if name == 'str': return types.STR
		assert len(types.Primitive) == 6, "Exhaustive check of Primitives, (implement next primitive type here)"
		typ,place = expand(self.type_names.get(name))
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.place, SemanticTokenType.TYPE,value_type=typ,def_place=place))
		if typ is None:
			self.config.errors.critical_error(ET.TYPE_REFERENCE, node.ref.place, f"type '{name}' is not defined")
		return typ
	def check_type_definition(self, node:nodes.TypeDefinition) -> Type:
		if self.semantic:
			self.semantic_tokens.add(SemanticToken(node.name.place, SemanticTokenType.TYPE, (SemanticTokenModifier.DEFINITION,)))
		self.type_names[node.name.operand] = self.check(node.typ),node.name.place
		return types.VOID
	def check_match(self, node:nodes.Match) -> Type:
		value = self.check(node.value)
		returns:list[tuple[Type,Place]] = []
		if isinstance(value, types.Enum):
			if self.semantic:
				self.semantic_tokens.add(SemanticToken(node.match_as.place, SemanticTokenType.VARIABLE, (SemanticTokenModifier.DECLARATION,)))
			for case in node.cases:
				names_before = self.names.copy()
				_, typ = node.lookup_enum(value, case, self.config)
				self.semantic_tokens.add(SemanticToken(case.name.place, SemanticTokenType.ENUM_ITEM, value_type=typ))
				self.names[node.match_as.operand] = typ,case.name.place
				returns.append((self.check(case.body),case.place))
				self.names = names_before
			if node.default is not None:
				returns.append((self.check(node.default),node.default.place))
		else:
			self.config.errors.add_error(ET.MATCH, node.place, f"matching type '{value}' is not supported")
		if len(returns) == 0:
			return types.VOID
		right_ret,_ = returns[0]
		for ret, place in returns:
			if ret != right_ret:
				self.config.errors.add_error(ET.MATCH, place, f"inconsistent branches: one branch returns, while other does not")
		if node.default is None:
			return types.VOID
		return right_ret
	def check(self, node:Node) -> Type:
		if type(node) == nodes.Assignment       : return self.check_assignment     (node)
		if type(node) == nodes.BinaryOperation  : return self.check_bin_exp        (node)
		if type(node) == nodes.Call             : return self.check_call           (node)
		if type(node) == nodes.Cast             : return self.check_cast           (node)
		if type(node) == nodes.CharNum          : return self.check_char_num       (node)
		if type(node) == nodes.CharStr          : return self.check_char_str       (node)
		if type(node) == nodes.Code             : return self.check_code           (node)
		if type(node) == nodes.Const            : return self.check_const          (node)
		if type(node) == nodes.Constant         : return self.check_constant       (node)
		if type(node) == nodes.Declaration      : return self.check_declaration    (node)
		if type(node) == nodes.Dot              : return self.check_dot            (node)
		if type(node) == nodes.Enum             : return self.check_enum           (node)
		if type(node) == nodes.ExprStatement    : return self.check_expr_state     (node)
		if type(node) == nodes.FromImport       : return self.check_from_import    (node)
		if type(node) == nodes.Fun              : return self.check_fun            (node)
		if type(node) == nodes.If               : return self.check_if             (node)
		if type(node) == nodes.Import           : return self.check_import         (node)
		if type(node) == nodes.Int              : return self.check_int            (node)
		if type(node) == nodes.Match            : return self.check_match          (node)
		if type(node) == nodes.Mix              : return self.check_mix            (node)
		if type(node) == nodes.ReferTo          : return self.check_refer          (node)
		if type(node) == nodes.Return           : return self.check_return         (node)
		if type(node) == nodes.Save             : return self.check_save           (node)
		if type(node) == nodes.Set              : return self.check_set            (node)
		if type(node) == nodes.Short            : return self.check_short          (node)
		if type(node) == nodes.Str              : return self.check_str            (node)
		if type(node) == nodes.StrCast          : return self.check_string_cast    (node)
		if type(node) == nodes.Struct           : return self.check_struct         (node)
		if type(node) == nodes.Subscript        : return self.check_get_item       (node)
		if type(node) == nodes.Template         : return self.check_template       (node)
		if type(node) == nodes.TypeArray        : return self.check_type_array     (node)
		if type(node) == nodes.TypeDefinition   : return self.check_type_definition(node)
		if type(node) == nodes.TypeFun          : return self.check_type_fun       (node)
		if type(node) == nodes.TypePointer      : return self.check_type_pointer   (node)
		if type(node) == nodes.TypeReference    : return self.check_type_reference (node)
		if type(node) == nodes.UnaryExpression  : return self.check_unary_exp      (node)
		if type(node) == nodes.Use              : return self.check_use            (node)
		if type(node) == nodes.Var              : return self.check_var            (node)
		if type(node) == nodes.VariableSave     : return self.check_variable_save  (node)
		if type(node) == nodes.While            : return self.check_while          (node)
		if type(node) == nodes.Assert           : return self.check_assert         (node)
		assert False, f"Unreachable, unknown {type(node)=}"
