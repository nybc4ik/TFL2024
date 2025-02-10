class RegexParserError(Exception):
    pass

class Lexeme:
    def __init__(self, token_type, value=None):
        self.token_type = token_type # тип лексемы (например CAP_OPEN для "(")
        self.value = value # дополнительная цифра (например при ссылке на выражение (?1))

    def __repr__(self):
        return f"Lexeme({self.token_type}, {self.value})"

# лексический анализатор
class RegexLexer:
    def __init__(self, input_text):
        self.input_text = input_text
        self.current_position = 0

    def look_ahead(self):
        if self.current_position < len(self.input_text):
            return self.input_text[self.current_position]
        return None

    def move_forward(self):
        self.current_position += 1

    def analyze_text(self):
        lexemes = []
        while self.current_position < len(self.input_text):
            current_char = self.look_ahead()
            if current_char == '(':
                self.move_forward()
                next_char = self.look_ahead()
                if next_char == '?':
                    self.move_forward()
                    next_next_char = self.look_ahead()
                    if next_next_char == ':':
                        self.move_forward()
                        lexemes.append(Lexeme('NONCAP_OPEN'))
                    elif next_next_char == '=':
                        self.move_forward()
                        lexemes.append(Lexeme('LOOKAHEAD_OPEN'))
                    elif next_next_char and next_next_char.isdigit():
                        self.move_forward()
                        value = int(next_next_char)
                        lexemes.append(Lexeme('EXPR_REF_OPEN', value))
                    else:
                        raise RegexParserError("Что-то не так после (?")
                else:
                    lexemes.append(Lexeme('CAP_OPEN'))
            elif current_char == ')':
                lexemes.append(Lexeme('CLOSE'))
                self.move_forward()
            elif current_char == '|':
                lexemes.append(Lexeme('ALT'))
                self.move_forward()
            elif current_char == '*':
                lexemes.append(Lexeme('STAR'))
                self.move_forward()
            elif current_char and 'a' <= current_char <= 'z':
                lexemes.append(Lexeme('CHAR', current_char))
                self.move_forward()
            else:
                raise RegexParserError(f"Что это? : {current_char}")
        return lexemes

# построение AST дерева и последущая проверка регекса по нему 
class GroupNode:
    def __init__(self, group_id, node):
        self.group_id = group_id
        self.node = node

    def __repr__(self):
        return f"GroupNode({self.group_id}, {self.node})"

class NonCapGroupNode:
    def __init__(self, node):
        self.node = node

    def __repr__(self):
        return f"NonCapGroupNode({self.node})"

class LookaheadNode:
    def __init__(self, node):
        self.node = node

    def __repr__(self):
        return f"LookaheadNode({self.node})"

class ConcatNode:
    def __init__(self, nodes):
        self.nodes = nodes

    def __repr__(self):
        return f"ConcatNode({self.nodes})"

class AltNode:
    def __init__(self, branches):
        self.branches = branches

    def __repr__(self):
        return f"AltNode({self.branches})"

class StarNode:
    def __init__(self, node):
        self.node = node

    def __repr__(self):
        return f"StarNode({self.node})"

class CharNode:
    def __init__(self, ch):
        self.ch = ch

    def __repr__(self):
        return f"CharNode('{self.ch}')"

class ExprRefNode:
    def __init__(self, ref_id):
        self.ref_id = ref_id

    def __repr__(self):
        return f"ExprRefNode({self.ref_id})"

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.group_count = 0
        self.max_groups = 9
        self.in_lookahead = False

        # group_id -> AST подграмматики
        self.groups_ast = {}

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def eat(self, token_type=None):
        tok = self.current_token()
        if tok is None:
            raise RegexParserError("Неожиданный конец выражения")
        if token_type is not None and tok.token_type != token_type:
            raise RegexParserError(f"Ожидается {token_type}, найдено {tok.token_type}")
        self.pos += 1
        return tok

    def parse(self):
        node = self.parse_alternation()
        if self.current_token() is not None:
            # на тот случай, если что-то осталось непрочитанное, то синтаксическая ошибка
            raise RegexParserError("Лишние символы после корректного выражения")
        # проверка синтаксической корректности
        self.check_references(node, defined_groups=set())
        return node

    def parse_alternation(self):
        # alternation: concatenation ('|' concatenation)*
        branches = [self.parse_concatenation()]
        while self.current_token() and self.current_token().token_type == 'ALT':
            self.eat('ALT')
            if self.current_token() is None or self.current_token().token_type in ['CLOSE', 'ALT']:
                raise RegexParserError("Пустая альтернатива запрещена")
            branches.append(self.parse_concatenation())
        if len(branches) == 1:
            return branches[0]
        return AltNode(branches)

    def parse_concatenation(self):
        # concatenation: repetition+
        nodes = []
        while self.current_token() and self.current_token().token_type not in ['CLOSE', 'ALT']:
            nodes.append(self.parse_repetition())
        if len(nodes) == 1:
            return nodes[0]
        return ConcatNode(nodes)

    def parse_repetition(self):
        # repetition: base ('*')?
        node = self.parse_base()
        while self.current_token() and self.current_token().token_type == 'STAR':
            self.eat('STAR')
            node = StarNode(node)
        return node

    def parse_base(self):
        tok = self.current_token()
        if tok is None:
            raise RegexParserError("Неожиданный конец при ожидании базового выражения")

        if tok.token_type == 'CAP_OPEN':
            # ( ... )
            self.eat('CAP_OPEN')
            self.group_count += 1
            if self.group_count > self.max_groups:
                raise RegexParserError("Превышено число групп захвата > 9")
            group_id = self.group_count
            node = self.parse_alternation()
            self.eat('CLOSE')
            self.groups_ast[group_id] = node
            return GroupNode(group_id, node)

        elif tok.token_type == 'NONCAP_OPEN':
            # (?: ... )
            self.eat('NONCAP_OPEN')
            node = self.parse_alternation()
            self.eat('CLOSE')
            return NonCapGroupNode(node)

        elif tok.token_type == 'LOOKAHEAD_OPEN':
            # (?= ... )
            if self.in_lookahead:
                raise RegexParserError("Вложенные опережающие проверки запрещены")
            self.eat('LOOKAHEAD_OPEN')
            old_look = self.in_lookahead
            self.in_lookahead = True
            node = self.parse_alternation()
            self.in_lookahead = old_look
            self.eat('CLOSE')
            return LookaheadNode(node)

        elif tok.token_type == 'EXPR_REF_OPEN':
            # (?N)
            ref_id = tok.value
            self.eat('EXPR_REF_OPEN')
            self.eat('CLOSE')
            return ExprRefNode(ref_id)

        elif tok.token_type == 'CHAR':
            ch = tok.value
            self.eat('CHAR')
            return CharNode(ch)

        else:
            raise RegexParserError(f"Некорректный токен: {tok}")

    def check_references(self, node, defined_groups):
        if isinstance(node, CharNode):
            return defined_groups

        elif isinstance(node, ExprRefNode):
            # тут рекурския 
            return defined_groups

        elif isinstance(node, GroupNode):
            # внутри группы сначала проверка содержимого
            new_defined = self.check_references(node.node, defined_groups)
            # после конца группы эта группа считается определённой
            new_defined = set(new_defined)
            new_defined.add(node.group_id)
            return new_defined

        elif isinstance(node, NonCapGroupNode):
            return self.check_references(node.node, defined_groups)

        elif isinstance(node, LookaheadNode):
            # необходимо проверить, что внутри нет групп захвата и нет других lookahead
            self.check_no_cap_and_lookahead(node.node, inside_lookahead=True)
            # тут ссылки на группы должны быть из уже определённых
            return self.check_references(node.node, defined_groups)

        elif isinstance(node, StarNode):
            return self.check_references(node.node, defined_groups)

        elif isinstance(node, ConcatNode):
            cur_defined = defined_groups
            for child in node.nodes:
                cur_defined = self.check_references(child, cur_defined)
            return cur_defined

        elif isinstance(node, AltNode):
            # сначала было пересечение, на теперь тут будет объединение,
            # чтобы ситуации вроде (a|(bb))(a|(?2)) были корректными
            all_defs = []
            for branch in node.branches:
                branch_defs = self.check_references(branch, defined_groups)
                all_defs.append(branch_defs)
            union_defs = set()
            for d in all_defs:
                union_defs.update(d)
            return union_defs

        else:
            raise RegexParserError("Неизвестный тип узла AST при проверке ссылок")

    def check_no_cap_and_lookahead(self, node, inside_lookahead): # проверка, что внутри лукахедов нет захватывающих групп и лукахедов       
        if isinstance(node, GroupNode) and inside_lookahead:
            raise RegexParserError("Внутри опережающей проверки не допускаются захватывающие группы")
        if isinstance(node, LookaheadNode) and inside_lookahead:
            raise RegexParserError("Внутри опережающей проверки не допускаются другие опережающие проверки")

        if isinstance(node, (NonCapGroupNode, LookaheadNode, StarNode, ConcatNode, AltNode)):
            # рекурсивная проверка для детей
            if isinstance(node, NonCapGroupNode):
                self.check_no_cap_and_lookahead(node.node, inside_lookahead)
            elif isinstance(node, LookaheadNode):
                self.check_no_cap_and_lookahead(node.node, inside_lookahead)
            elif isinstance(node, StarNode):
                self.check_no_cap_and_lookahead(node.node, inside_lookahead)
            elif isinstance(node, ConcatNode):
                for n in node.nodes:
                    self.check_no_cap_and_lookahead(n, inside_lookahead)
            elif isinstance(node, AltNode):
                for b in node.branches:
                    self.check_no_cap_and_lookahead(b, inside_lookahead)

# тестирование

test_patterns = [
    "()",  # Пустая группа
    "(a|b)(c|d)(e|f)(g|h)(i|j)(k|l)(m|n)(o|p)(q|r)",  # 9 групп
    "(a|b)(c|d)(e|f)(g|h)(i|j)(k|l)(m|n)(o|p)(q|r)(s|t)",  # 10 групп (ошибка)
    "((?1))",  # Правильная рекурсия
    "*a",
    "a))",
    "()",  # не ок
    "(a|b)(?=c)",  # ок
    "a)",
    "a|",
    "|a",
    "(a|*)",
    "(a|(ab))",
    "(a|*)",
    "((?=ab*(?:a|a*))(a|b))*aa",  # ок
    "(a*)*(?=a)*",  # ок
    "((?=ab*(a|a*))(a|b))*aa",  # не ок
    "aaa|(?=ab)a*b*a*",
    "(a|b)c*", 
]


for test in test_patterns:
    print("\nРазбор на лексемы: ", test)
    try:
        lexer = RegexLexer(test)
        tokens = lexer.analyze_text()
        for token in tokens:
            print(token)
        print()
        # проверка регекса
        print("Проверка регексов, если регекс правильный, то будет его дерево, иначе ошибка: ")
        parser = Parser(tokens)
        ast = parser.parse()
        print("Дерево: ", ast)
    except RegexParserError as e:
        print("Ошибка:", e)
