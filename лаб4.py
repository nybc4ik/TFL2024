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
    "(a|b)c*"
]

for test in test_patterns:
    print("разбор на лексемы: ", test)
    lexer = RegexLexer(test)
    tokens = lexer.analyze_text()
    for token in tokens:
        print(token)
    print()
