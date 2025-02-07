import re

# часть 1 чтение грамматики и преобразование её в более удобный для дальнейшей обработки вид!
def parse_grammar(lines):
    """
    Тут разбор грамматики, например такой:
        S -> [SS1]ab | aa | [SS1]b | SS | A
        [SS1] -> [SS1]S | S
        A -> S S | bb
    
    По условию вот такая вот у нас грамматика :
      - Левая часть: [NT] (например, S или [SS1])
      - '->'
      - Правая часть: несколько альтернатив, разделённых символом '|'
      - В каждой альтернативе — последовательность NT или T
        (нетерминалы в квадратных скобках или в верхнем регистре, 
         терминалы в нижнем регистре)
         
    В результате преобразования мы должны получить что-то такое:
       grammar = {
         "S": [ ["[SS1]","a","b"], ["a","a"], ["[SS1]","b"], ["S","S"], ["A"] ],
         "[SS1]": [ ["[SS1]","S"], ["S"] ],
         "A": [ ["S","S"], ["b","b"] ]
       }
       Ну и конечно же не забыть про ! start_symbol это такой нетерминал, который встретился первым (попался!)
    """
    grammar = {}
    start_symbol = None
    
    # тут регулярное выражение для вытаскивания нетерминалов в квадратных скобках и обычных
    # пример нетерминала [SS1] или S, A, B2 и т.п.
    # пример терминала a, b, c ...
    nonterminal_pattern = re.compile(r'(\[[A-Z0-9]+\]|[A-Z][0-9A-Z]*)')
    
    def tokenize_right_side(rhs):
        """
        нужно разбить правую часть правила на отдельные символы (NT или T)
        примерно так: '[SS1]ab' -> ['[SS1]', 'a', 'b']
        или так: 'S S'  -> ['S', 'S']
        """
        tokens = []
        # тут удаление пробелов
        chunk = rhs.strip()    
      
        # если есть пробелы, то нужно использовать split
        if ' ' in chunk:
            parts = chunk.split()
        else:
            # если нет пробелов
            parts = [chunk]
        
        result_tokens = []
        
        for part in parts:
            # в каждом куске нужно найти нетерминалы в скобках через finditer:
            idx = 0
            for m in nonterminal_pattern.finditer(part):
                start, end = m.span()
                # но всё, что слева до нетерминала - это терминальные символы (по одиночке)
                if start > idx:
                    # Например, 'ab'
                    sub = part[idx:start]
                    for c in sub:
                        result_tokens.append(c)  # одиночные символы
                # если нашли нетерминал, то добавляем
                result_tokens.append(m.group(0))
                idx = end
            # если остался хвост
            if idx < len(part):
                sub = part[idx:]
                for c in sub:
                    result_tokens.append(c)        
        return result_tokens

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        left_right = line.split('->')
        if len(left_right) != 2:
            raise ValueError(f"Ошибка в строке '{line}' — нет '->' или их больше одного.")
        left = left_right[0].strip()
        right = left_right[1].strip()
        
        # поиск левой части (нетерминал)
        # и проверка, что левая часть похожа на NT в соответствии с форматом
        left_nt_match = nonterminal_pattern.fullmatch(left)
        if not left_nt_match:
            raise ValueError(f"Неверный формат нетерминала слева: '{left}'")
        left_nt = left_nt_match.group(0)
        
        # сохранение первого нетерминала как стартового символа, но только если он ещё не задан
        if start_symbol is None:
            start_symbol = left_nt
        
        # разделение провой части по '|'
        alternatives = right.split('|')
        
        rules = []
        for alt in alternatives:
            alt = alt.strip()
            # тут нужно рзабить альтернативу на последовательность символов
            tokens = tokenize_right_side(alt)
            if not tokens:
                # но если вдруг правая часть пустая (ε-правило), то нужно написать особый символ
                tokens = ["ε"]  #  если что это "ε" эпсилон или же пустота
            rules.append(tokens)
        
        if left_nt not in grammar:
            grammar[left_nt] = []
        grammar[left_nt].extend(rules)
    return grammar, start_symbol

# часть 2 тут удаление правил
def remove_rules(grammar, start_symbol):
    """
    Тут удаляются правила вида A -> C C -> B 
    И возвращается обновлённая грамматика, где таких правил нет
    """
    nonterminals = list(grammar.keys())
    # reachable[A] = множество нетерминалов, достижимых из A с помощью подобных правил
    reachable = {A: set() for A in nonterminals}
    
    for A in nonterminals:
        reachable[A].add(A)
    
    for A in nonterminals:
        # поиск правил A -> B, где B нетерминал
        queue = deque()
        # сначала те B, которые непосредственно идут из A
        for rule in grammar[A]:
            if len(rule) == 1:
                candidate = rule[0]
                if candidate in grammar:  # тут candidate - нетерминал
                    queue.append(candidate)
        
        while queue:
            B = queue.popleft()
            if B not in reachable[A]:
                reachable[A].add(B)
                # теперь добавление всего, куда ведёт B
                for ruleB in grammar[B]:
                    if len(ruleB) == 1:
                        cand2 = ruleB[0]
                        if cand2 in grammar and cand2 not in reachable[A]:
                            queue.append(cand2)
    
    # удаляем всех подобных правил
    new_grammar = {}
    for A in nonterminals:
        new_rules = []
        for rule in grammar[A]:
            # если правило A -> B, и B нетерминал, то это то что нужно! — удаляем.
            if len(rule) == 1 and rule[0] in grammar:
                continue
            else:
                new_rules.append(rule)
        new_grammar[A] = new_rules
    
    # добавляение недостающих правил
    for A in nonterminals:
        for B in reachable[A]:
            for ruleB in grammar[B]:
                if not (len(ruleB) == 1 and ruleB[0] in grammar):
                    if ruleB not in new_grammar[A]:  # чтобы не дублировать
                        new_grammar[A].append(ruleB)
    
    return new_grammar, start_symbol


# небольшие тесты 

grammar = [
    "S -> S S | a | S"
]

print('проверка грамматики после преобразования ')
grammar1, start_symbol = parse_grammar(grammar)

print (grammar1, start_symbol)


grammar = [
    "S -> [SS1]ab|aa|[SS1]b|SS|A",
    "[SS1] -> [SS1]S|S",
    "A -> S S | bb"
]

print('проверка грамматики после преобразования ')
grammar1, start_symbol = parse_grammar(grammar)

print (grammar1, start_symbol)

print("после удаления правил: ")

new_grammar, start_symbol = remove_rules(grammar1, start_symbol)

print(new_grammar)


