from .primitives import Node, nodes, TT, Token, NEWLINE, Config, find_fun_by_name, id_counter, INTRINSICS_TYPES, Type, types
from dataclasses import dataclass
__INTRINSICS_IMPLEMENTATION:'dict[str,str]' = {
	'exit':f"""declare void @exit(i32)
define void @exit_({types.INT.llvm} %0) {{
	%2 = trunc i64 %0 to i32
	call void @exit(i32 %2)
	unreachable
}}\n""",
	'write':f"""declare i32 @write(i32,i8*,i32)
define {types.INT.llvm} @write_({types.INT.llvm} %0,{types.STR.llvm} %1) {{
	%3 = extractvalue {types.STR.llvm} %1, 0
	%4 = extractvalue {types.STR.llvm} %1, 1
	%5 = trunc {types.INT.llvm} %0 to i32
	%6 = trunc {types.INT.llvm} %3 to i32
	%7 = call i32 @write(i32 %5,i8* %4,i32 %6)
	%8 = zext i32 %7 to {types.INT.llvm}
	ret {types.INT.llvm} %8
}}\n""",
	'read':f"""declare i32 @read(i32,i8*,i32)
define {types.INT.llvm} @read_({types.INT.llvm} %0, {types.PTR.llvm} %1, {types.INT.llvm} %2) {{
	%4 = trunc {types.INT.llvm} %0 to i32
	%5 = bitcast {types.PTR.llvm} %1 to i8*
	%6 = trunc {types.INT.llvm} %2 to i32
	%7 = call i32 @read(i32 %4, i8* %5, i32 %6)
	%8 = zext i32 %7 to {types.INT.llvm}
	ret {types.INT.llvm} %8
}}\n""",
	'ptr':f"""
define {types.PTR.llvm} @ptr_({types.STR.llvm} %0) {{
	%2 = extractvalue {types.STR.llvm} %0, 1
	%3 = bitcast i8* %2 to {types.PTR.llvm}
	ret {types.PTR.llvm} %3
}}\n""",
	'len':f"""
define {types.INT.llvm} @len_({types.STR.llvm} %0) {{
	%2 = extractvalue {types.STR.llvm} %0, 0
	ret {types.INT.llvm} %2
}}\n""",
	'str':f"""
define {types.STR.llvm} @str_({types.INT.llvm} %0, {types.PTR.llvm} %1) {{
	%3 = bitcast {types.PTR.llvm} %1 to i8*
	%4 = insertvalue {types.STR.llvm} undef, i64 %0, 0
	%5 = insertvalue {types.STR.llvm} %4, i8* %3, 1
	ret {types.STR.llvm} %5
}}\n""",
	'load_byte':f"""
define {types.INT.llvm} @load_byte_({types.PTR.llvm} %0) {{
	%2 = load i8, {types.PTR.llvm} %0
	%3 = zext i8 %2 to {types.INT.llvm}
	ret {types.INT.llvm} %3
}}\n""",
	'save_byte':f"""
define void @save_byte_({types.PTR.llvm} %0, {types.INT.llvm} %1) {{
	%3 = trunc {types.INT.llvm} %1 to i8
	store i8 %3, {types.PTR.llvm} %0
	ret void
}}\n""",
	'load_int':f"""
define {types.INT.llvm} @load_int_({types.Ptr(types.INT).llvm} %0) {{
	%2 = load {types.INT.llvm}, {types.Ptr(types.INT).llvm} %0
	ret {types.INT.llvm} %2
}}\n""",
	'save_int':f"""
define void @save_int_({types.Ptr(types.INT).llvm} %0, {types.INT.llvm} %1) {{
	store {types.INT.llvm} %1, {types.Ptr(types.INT).llvm} %0
	ret void
}}\n""",
	'nanosleep':f"""declare i32 @nanosleep({{i64, i64}}*, {{i64, i64}}*)
define {types.INT.llvm} @nanosleep_({types.PTR.llvm} %0, {types.PTR.llvm} %1) {{
	%3 = bitcast {types.PTR.llvm} %0 to {{i64, i64}}*
	%4 = bitcast {types.PTR.llvm} %1 to {{i64, i64}}*
	%5 = call i32 @nanosleep({{i64, i64}}* %3, {{i64, i64}}* %4)
	%6 = zext i32 %5 to {types.INT.llvm}
	ret {types.INT.llvm} %6
}}\n""",
	'fcntl':f"""declare i32 @fcntl(i32, i32, ...)
define {types.INT.llvm} @fcntl_({types.INT.llvm} %0, {types.INT.llvm} %1, {types.INT.llvm} %2){{
	%4 = trunc {types.INT.llvm} %0 to i32
	%5 = trunc {types.INT.llvm} %1 to i32
	%6 = trunc {types.INT.llvm} %2 to i32
	%7 = call i32 @fcntl(i32 %4, i32 %5, i32 %6)
	%8 = zext i32 %7 to {types.INT.llvm}
	ret {types.INT.llvm} %8
}}\n""",
	'tcsetattr':f"""declare i32 @tcsetattr(i32, i32, {{i32,i32,i32,i32,i8,[32 x i8],i32,i32}}*)
define {types.INT.llvm} @tcsetattr_({types.INT.llvm} %0, {types.INT.llvm} %1, {types.PTR.llvm} %2) {{
	%4 = trunc {types.INT.llvm} %0 to i32
	%5 = trunc {types.INT.llvm} %1 to i32
	%6 = bitcast {types.PTR.llvm} %2 to {{i32,i32,i32,i32,i8,[32 x i8],i32,i32}}*
	%7 = call i32 @tcsetattr(i32 %4, i32 %5, {{i32,i32,i32,i32,i8,[32 x i8],i32,i32}}* %6)
	%8 = zext i32 %7 to {types.INT.llvm}
	ret {types.INT.llvm} %8
}}\n""",
	'tcgetattr':f"""declare i32 @tcgetattr(i32, {{i32,i32,i32,i32,i8,[32 x i8],i32,i32}}*)
define {types.INT.llvm} @tcgetattr_({types.INT.llvm} %0, {types.PTR.llvm} %1) {{
	%3 = trunc {types.INT.llvm} %0 to i32
	%4 = bitcast {types.PTR.llvm} %1 to {{i32,i32,i32,i32,i8,[32 x i8],i32,i32}}*
	%5 = call i32 @tcgetattr(i32 %3, {{i32,i32,i32,i32,i8,[32 x i8],i32,i32}}* %4)
	%6 = zext i32 %5 to {types.INT.llvm}
	ret {types.INT.llvm} %6
}}\n""",
}
assert len(__INTRINSICS_IMPLEMENTATION) == len(INTRINSICS_TYPES), f"{len(__INTRINSICS_IMPLEMENTATION)} != {len(INTRINSICS_TYPES)}"
INTRINSICS_IMPLEMENTATION:'dict[int,tuple[str,str]]' = {
	INTRINSICS_TYPES[name][2]:(name,__INTRINSICS_IMPLEMENTATION[name]) for name in __INTRINSICS_IMPLEMENTATION
}
@dataclass(slots=True, frozen=True)
class TV:#typed value
	typ:'Type|None'  = None
	val:'str' = ''
	def __str__(self) -> str:
		if self.typ is None:
			return f"<None TV>"
		return f"{self.typ.llvm} {self.val}"
class GenerateAssembly:
	__slots__ = ('text','ast','config', 'variables', 'structs', 'consts', 'memos', 'funs', 'vars', 'strings', 'intrnsics')
	def __init__(self, ast:nodes.Tops, config:Config) -> None:
		self.config   :Config                    = config
		self.ast      :nodes.Tops                = ast
		self.text     :str                       = ''
		self.vars     :list[nodes.Var]           = []
		self.memos    :list[nodes.Memo]          = []
		self.consts   :list[nodes.Const]         = []
		self.structs  :list[nodes.Struct]        = []
		self.strings  :list[Token]               = []
		self.variables:list[nodes.TypedVariable] = []
		self.intrnsics:set[int]                  = set()
		self.generate_assembly()
	def visit_fun(self, node:nodes.Fun) -> TV:
		assert self.variables == [], f"visit_fun called with {[str(var) for var in self.variables]} (vars should be on the stack) at {node}"
		self.variables = node.arg_types.copy()
		ot = node.output_type
		self.text += f"""
define {ot.llvm} @fun_{node.uid}\
({', '.join(f'{arg.typ.llvm} %argument{arg.uid}' for arg in node.arg_types)}) {{
{f'	%retvar = alloca {ot.llvm}{NEWLINE}' if ot != types.VOID else ''}\
{''.join(f'''	%v{arg.uid} = alloca {arg.typ.llvm}
	store {arg.typ.llvm} %argument{arg.uid}, {types.Ptr(arg.typ).llvm} %v{arg.uid},align 4
''' for arg in node.arg_types)}"""
		self.visit(node.code)


		self.text += f"""\
	{f'br label %return' if ot == types.VOID else 'unreachable'}
return:
{f'	%retval = load {ot.llvm}, {ot.llvm}* %retvar{NEWLINE}' if ot != types.VOID else ''}\
	ret {ot.llvm} {f'%retval' if ot != types.VOID else ''}
}}
"""
		self.variables = []
		return TV()
	def visit_code(self, node:nodes.Code) -> TV:
		var_before = self.variables.copy()
		for statemnet in node.statements:
			self.visit(statemnet)
		self.variables = var_before
		return TV()
	def visit_function_call(self, node:nodes.FunctionCall) -> TV:
		args = [self.visit(arg) for arg in node.args]
		intrinsic = INTRINSICS_TYPES.get(node.name.operand)
		rt:Type
		if intrinsic is not None:
			rt = intrinsic[1]
			self.intrnsics.add(intrinsic[2])
			name = f"@{node.name.operand}_"
		else:
			fun = find_fun_by_name(self.ast, node.name)
			rt = fun.output_type
			name = f"@fun_{fun.uid}"
		self.text+='\t'
		if rt != types.VOID:
			self.text+=f"""\
%callresult{node.uid} = """

		self.text += f"""\
call {rt.llvm} {name}({', '.join(str(a) for a in args)})
"""
		if rt != types.VOID:
			return TV(rt, f"%callresult{node.uid}")
		return TV(types.VOID)
	def visit_token(self, token:Token) -> TV:
		if token.typ == TT.NUMBER:
			return TV(types.INT, token.operand)
		elif token.typ == TT.STRING:
			self.strings.append(token)
			l = len(token.operand)
			u = token.uid
			return TV(types.STR,f"<{{i64 {l}, i8* bitcast([{l} x i8]* @.str.{u} to i8*)}}>")
		else:
			assert False, f"Unreachable: {token.typ=}"
	def visit_bin_exp(self, node:nodes.BinaryExpression) -> TV:
		left = self.visit(node.left)
		right = self.visit(node.right)
		lr = left.typ,right.typ
		lv = left.val
		rv = right.val
		operations = {
			TT.PERCENT_SIGN:             f"srem {types.INT.llvm} {lv}, {rv}",
			TT.MINUS:                 f"sub nsw {types.INT.llvm} {lv}, {rv}",
			TT.ASTERISK:              f"mul nsw {types.INT.llvm} {lv}, {rv}",
			TT.DOUBLE_SLASH:             f"sdiv {types.INT.llvm} {lv}, {rv}",
			TT.LESS_SIGN:            f"icmp slt {types.INT.llvm} {lv}, {rv}",
			TT.LESS_OR_EQUAL_SIGN:   f"icmp sle {types.INT.llvm} {lv}, {rv}",
			TT.GREATER_SIGN:         f"icmp sgt {types.INT.llvm} {lv}, {rv}",
			TT.GREATER_OR_EQUAL_SIGN:f"icmp sge {types.INT.llvm} {lv}, {rv}",
			TT.DOUBLE_EQUALS_SIGN:    f"icmp eq {types.INT.llvm} {lv}, {rv}",
			TT.NOT_EQUALS_SIGN:       f"icmp ne {types.INT.llvm} {lv}, {rv}",
			TT.DOUBLE_LESS_SIGN:          f"shl {types.INT.llvm} {lv}, {rv}",
			TT.DOUBLE_GREATER_SIGN:      f"ashr {types.INT.llvm} {lv}, {rv}",
}
		op = node.operation
		implementation:'None|str' = None
		if   op == TT.PLUS:
			if lr == (types.INT,types.INT):implementation = f'add nsw {types.INT.llvm} {lv}, {rv}'
			if lr == (types.PTR,types.INT):
				self.text +=f"""\
	%tmp1{node.uid} = ptrtoint {left} to i64
	%tmp2{node.uid} = add i64 %tmp1{node.uid}, {rv}
"""
				implementation = f'inttoptr i64 %tmp2{node.uid} to ptr'
		elif op.equals(TT.KEYWORD,'and'):
			if lr == (types.INT ,types.INT ):implementation = f'and {types.INT .llvm} {lv}, {rv}'
			if lr == (types.BOOL,types.BOOL):implementation = f'and {types.BOOL.llvm} {lv}, {rv}'
		elif op.equals(TT.KEYWORD,'or' ):
			if lr == (types.INT ,types.INT ):implementation = f'or { types.INT .llvm} {lv}, {rv}'
			if lr == (types.BOOL,types.BOOL):implementation = f'or { types.BOOL.llvm} {lv}, {rv}'
		elif op.equals(TT.KEYWORD,'xor'):
			if lr == (types.INT ,types.INT ):implementation = f'xor {types.INT .llvm} {lv}, {rv}'
			if lr == (types.BOOL,types.BOOL):implementation = f'xor {types.BOOL.llvm} {lv}, {rv}'
		else:
			implementation = operations.get(node.operation.typ)
		assert implementation is not None, f"op '{node.operation}' is not implemented yet"
		self.text+=f"""\
	%bin_op{node.uid} = {implementation}
"""


		return TV(node.typ(left.typ, right.typ), f"%bin_op{node.uid}")
	def visit_expr_state(self, node:nodes.ExprStatement) -> TV:
		self.visit(node.value)
		return TV()
	def visit_refer(self, node:nodes.ReferTo) -> TV:
		def refer_to_var(var:nodes.Var) -> TV:
			return TV(types.Ptr(var.typ),
				f"@.var.{var.uid}"
			)
		def refer_to_memo(memo:nodes.Memo) -> TV:
			return TV(types.PTR,
				f"bitcast([{memo.size} x i8]* \
@.memo.{memo.uid} to {types.PTR.llvm})"
			)
		def refer_to_const(const:nodes.Const) -> TV:
			return TV(types.INT,f"{const.value}")

		def refer_to_variable() -> TV:
			for variable in self.variables:
				if node.name == variable.name:
					typ = variable.typ
					self.text+=f"""\
	%refer{node.uid} = load {typ.llvm}, {types.Ptr(typ).llvm} %v{variable.uid}
"""
					return TV(typ,f'%refer{node.uid}')
			assert False, "type checker is broken"
		for var in self.vars:
			if node.name == var.name:
				return refer_to_var(var)
		for memo in self.memos:
			if node.name == memo.name:
				return refer_to_memo(memo)
		for const in self.consts:
			if node.name == const.name:
				return refer_to_const(const)
		return refer_to_variable()
	def visit_defining(self, node:nodes.Defining) -> TV:
		self.variables.append(node.var)
		self.text += f"""\
	%v{node.var.uid} = alloca {node.var.typ.llvm}
"""
		return TV()
	def visit_reassignment(self, node:nodes.ReAssignment) -> TV:
		val = self.visit(node.value)
		for variable in self.variables:
			if node.name == variable.name:
				var = variable
				break
		else:
			assert False, "type checker does not work"
		self.text += f"""\
	store {val}, {types.Ptr(val.typ).llvm} %v{var.uid},align 4
"""
		return TV()
	def visit_assignment(self, node:nodes.Assignment) -> TV:
		val = self.visit(node.value) # get a value to store
		self.variables.append(node.var)
		self.text += f"""\
	%v{node.var.uid} = alloca {node.var.typ.llvm}
	store {val}, {types.Ptr(val.typ).llvm} %v{node.var.uid},align 4
"""
		return TV()
	def visit_if(self, node:nodes.If) -> TV:
		cond = self.visit(node.condition)
		self.text+=f"""\
	br {cond}, label %ift{node.uid}, label %iff{node.uid}
ift{node.uid}:
"""
		self.visit(node.code)
		self.text+=f"""\
	br label %ife{node.uid}
iff{node.uid}:
"""
		if node.else_code is not None:
			self.visit(node.else_code)
		self.text+=f"""\
	br label %ife{node.uid}
ife{node.uid}:
"""
		return TV()
	def visit_while(self, node:nodes.While) -> TV:
		self.text+=f"""\
	br label %whilec{node.uid}
whilec{node.uid}:
"""
		cond = self.visit(node.condition)
		self.text+=f"""\
	br {cond}, label %whileb{node.uid}, label %whilee{node.uid}
whileb{node.uid}:
"""
		self.visit(node.code)
		self.text+=f"""\
	br label %whilec{node.uid}
whilee{node.uid}:
"""
		return TV()
	def visit_intr_constant(self, node:nodes.IntrinsicConstant) -> TV:
		constants = {
			'False':TV(types.BOOL,'0'),
			'True' :TV(types.BOOL,'1'),
		}
		implementation = constants.get(node.name.operand)
		assert implementation is not None, f"Constant {node.name} is not implemented yet"
		return implementation
	def visit_unary_exp(self, node:nodes.UnaryExpression) -> TV:
		val = self.visit(node.left)
		l = val.typ
		op = node.operation
		if   op == TT.NOT: i = f'xor {val}, -1'
		else:
			assert False, f"Unreachable, {op = } and {l = }"
		self.text+=f"""\
	%uo{node.uid} = {i}
"""

		return TV(node.typ(l),f"%uo{node.uid}")
	def visit_var(self, node:nodes.Var) -> TV:
		self.vars.append(node)
		return TV()
	def visit_memo(self, node:nodes.Memo) -> TV:
		self.memos.append(node)
		return TV()
	def visit_const(self, node:nodes.Const) -> TV:
		self.consts.append(node)
		return TV()
	def visit_struct(self, node:nodes.Struct) -> TV:
		self.structs.append(node)
		return TV()
	def visit_return(self, node:nodes.Return) -> TV:
		rv = self.visit(node.value)
		self.text += f"""\
	store {rv}, {types.Ptr(rv.typ).llvm} %retvar
	br label %return
"""
		return TV()
	def visit_dot(self, node:nodes.Dot) -> TV:
		origin = self.visit(node.origin)
		assert isinstance(origin.typ,types.Ptr), f'dot lookup is not supported for {origin} yet'
		pointed = origin.typ.pointed
		if isinstance(pointed, types.Struct):
			idx,typ = node.lookup_struct(pointed.struct)
			self.text += f"""\
	%dot{node.uid} = getelementptr inbounds {pointed.llvm}, {origin}, i32 0, i32 {idx}
"""
			return TV(types.Ptr(typ),f"%dot{node.uid}")
		else:
			assert False, f'unreachable, unknown {type(origin.typ.pointed) = }'
	def visit_get_item(self, node:nodes.GetItem) -> TV:
		origin = self.visit(node.origin)
		subscript = self.visit(node.subscript)
		assert isinstance(origin.typ,types.Ptr), "unreachable"
		pointed = origin.typ.pointed
		if isinstance(pointed, types.Array):
			self.text +=f"""\
	%gi{node.uid} = getelementptr inbounds {pointed.llvm}, {origin}, i32 0, {subscript}
"""
			return TV(types.Ptr(pointed.typ),f'%gi{node.uid}')
		else:
			assert False, 'unreachable'
	def visit_cast(self, node:nodes.Cast) -> TV:
		val = self.visit(node.value)
		nt = node.typ
		vt = val.typ
		if   (isinstance(vt,types.Ptr) or vt == types.PTR) and (isinstance(nt,types.Ptr) or nt == types.PTR):op = 'bitcast'
		elif (vt,nt) ==(types.BOOL,types.INT):op = 'zext'
		elif (vt,nt) ==(types.INT,types.BOOL):op = 'trunc'
		elif (vt,nt) ==(types.INT,types.PTR ):op = 'inttoptr'
		else:
			assert False, f"cast {vt} -> {nt} is not implemented yet"
		self.text += f"""\
	%cast{node.uid} = {op} {val} to {node.typ.llvm}
"""
		return TV(node.typ,f'%cast{node.uid}')
	def visit(self, node:'Node|Token') -> TV:
		if type(node) == nodes.Fun              : return self.visit_fun          (node)
		if type(node) == nodes.Var              : return self.visit_var          (node)
		if type(node) == nodes.Memo             : return self.visit_memo         (node)
		if type(node) == nodes.Const            : return self.visit_const        (node)
		if type(node) == nodes.Struct           : return self.visit_struct       (node)
		if type(node) == nodes.Code             : return self.visit_code         (node)
		if type(node) == nodes.FunctionCall     : return self.visit_function_call(node)
		if type(node) == nodes.BinaryExpression : return self.visit_bin_exp      (node)
		if type(node) == nodes.UnaryExpression  : return self.visit_unary_exp    (node)
		if type(node) == nodes.ExprStatement    : return self.visit_expr_state   (node)
		if type(node) == nodes.Assignment       : return self.visit_assignment   (node)
		if type(node) == nodes.ReferTo          : return self.visit_refer        (node)
		if type(node) == nodes.Defining         : return self.visit_defining     (node)
		if type(node) == nodes.ReAssignment     : return self.visit_reassignment (node)
		if type(node) == nodes.If               : return self.visit_if           (node)
		if type(node) == nodes.While            : return self.visit_while        (node)
		if type(node) == nodes.Return           : return self.visit_return       (node)
		if type(node) == nodes.IntrinsicConstant: return self.visit_intr_constant(node)
		if type(node) == nodes.Dot              : return self.visit_dot          (node)
		if type(node) == nodes.GetItem          : return self.visit_get_item     (node)
		if type(node) == nodes.Cast             : return self.visit_cast         (node)
		if type(node) == Token                  : return self.visit_token        (node)
		assert False, f'Unreachable, unknown {type(node)=} '
	def generate_assembly(self) -> None:
		text="""\
; Assembly generated by lang compiler github.com/izumrudik/compile
; ---------------------------
"""
		for top in self.ast.tops:
			self.visit(top)
		for struct in self.structs:
			text += f"{types.Struct(struct).llvm} = type {{{', '.join(var.typ.llvm for var in struct.variables)}}}\n"
		for uid in self.intrnsics:
			text += INTRINSICS_IMPLEMENTATION[uid][1]
		for memo in self.memos:
			text += f"@.memo.{memo.uid} = global [{memo.size} x i8] zeroinitializer, align 1\n"
		for var in self.vars:
			text += f"@.var.{var.uid} = global {var.typ.llvm} zeroinitializer, align 1\n"
		for string in self.strings:
			l = len(string.operand)
			st = ''.join('\\'+('0'+hex(ord(c))[2:])[-2:] for c in string.operand)
			text += f"@.str.{string.uid} = constant [{l} x i8] c\"{st}\", align 1"
		for top in self.ast.tops:
			if isinstance(top, nodes.Fun):
				if top.name.operand == 'main':break
		else:assert False, "Type checker is not responding"
		main_top = top
		text += f"""
define i64 @main(){{;entry point
	call void @fun_{main_top.uid}()
	ret i64 0
}}
"""
		self.text = text+self.text
		if self.config.verbose:
			self.text+=f"""
; ---------------------------
; DEBUG:
; there was {len(self.ast.tops)} tops
; constant values:
{''.join(f';	{const.name} = {const.value}{NEWLINE}' for const in self.consts)
}; state of id counter: {id_counter}
"""
		if self.config.interpret:
			return
		with open(self.config.output_file + '.ll', 'wt', encoding='UTF-8') as file:
			file.write(self.text)
