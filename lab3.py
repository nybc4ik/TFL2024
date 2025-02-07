import re
from collections import defaultdict, deque

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


# основа (БАЗА) программы находится тут ... ЧАСТЬ 3 построение PDA на основе LR(0)

class LR0Item:
    """
    Класс для LR(0)-item.
    Пример item: (A -> aB), где:
      left = A
      right = ['a', 'B'] (список символов в правой части)
      dot_pos = позиция точки
    """
    __slots__ = ['left', 'right', 'dot_pos']
    
    def __init__(self, left, right, dot_pos=0): 
        self.left = left
        self.right = right
        self.dot_pos = dot_pos

    def __eq__(self, other): 
        return (self.left == other.left and
                self.right == other.right and
                self.dot_pos == other.dot_pos)
    
    def __hash__(self): 
        return hash((self.left, tuple(self.right), self.dot_pos))
    
    def __repr__(self): 
        # пример: S -> A . b B
        rhs = self.right.copy()
        rhs.insert(self.dot_pos, "·")
        return f"{self.left} -> {' '.join(rhs)}"

def closure(items, grammar):
    closure_set = set(items)
    changed = True
    while changed:
        changed = False
        new_items = set()
        
        for it in closure_set:
            # если точка не в конце и символ после точки - нетерминал B
            if it.dot_pos < len(it.right):
                symbol = it.right[it.dot_pos]
                if symbol in grammar:  # значит это нетерминал
                    for rule in grammar[symbol]:
                        new_item = LR0Item(symbol, rule, 0)
                        if new_item not in closure_set:
                            new_items.add(new_item)
        
        if new_items:
            closure_set |= new_items
            changed = True
    
    return closure_set

def goto(items, symbol, grammar):   
    moved = set()
    for it in items:
        if it.dot_pos < len(it.right):
            if it.right[it.dot_pos] == symbol:
                # сдвигаем точку
                moved.add(LR0Item(it.left, it.right, it.dot_pos+1))
    return closure(moved, grammar)

def build_lr0_automaton(grammar, start_symbol):
    augmented_start = f"{start_symbol}'"  # S'
    while augmented_start in grammar:
        augmented_start += "'"
    # добавляем новое правило: S' -> S
    # (предполагаем, что start_symbol не был ранее в скобках)
    grammar[augmented_start] = [[start_symbol]]
    
    # список для хранения уникальных состояний 
    states = []
    # а это чтобы быстро находить индекс состояния по множеству 
    states_map = {}
    
    # переходы 
    transitions = defaultdict(list)
    
    # начальное состояние
    start_item = LR0Item(augmented_start, [start_symbol], 0)
    I0 = closure({start_item}, grammar)
    
    states.append(I0)
    states_map[frozenset(I0)] = 0
    
    queue = deque([0])
    
    # тут символы грамматики (все нетерминалы + терминалы) 
    # их можно собрать из grammar
    all_symbols = set()
    for A, rules in grammar.items():
        all_symbols.add(A)  # как символ (нетерминал) - хотя для GOTO это иногда лишнее
        for r in rules:
            for sym in r:
                all_symbols.add(sym)
    # но в реальности для GOTO нужны все символы, кроме ε   
    if "ε" in all_symbols:
        all_symbols.remove("ε")
    
    while queue:
        s_idx = queue.popleft()
        state_items = states[s_idx]
        
        # для каждого символа строим GOTO(state_items, symbol)
        for sym in all_symbols:
            nxt = goto(state_items, sym, grammar)
            if not nxt:
                continue
            # и проверка, есть ли уже такое состояние
            fznxt = frozenset(nxt)
            if fznxt not in states_map:
                new_idx = len(states)
                states.append(nxt)
                states_map[fznxt] = new_idx
                queue.append(new_idx)
                transitions[(s_idx, sym)].append(new_idx)
            else:
                transitions[(s_idx, sym)].append(states_map[fznxt])
    
    return states, transitions, augmented_start


# часть 4 для проверки принадлежности строки нужно построить таблицу действий (ACTION, GOTO) и простой парсер LR(0)

def build_lr0_parse_table(states, transitions, grammar, augmented_start):
    action_table = defaultdict(lambda: defaultdict(list))
    goto_table = defaultdict(lambda: defaultdict(list))
    
    # список нетерминалов и терминалов
    nonterminals = set(grammar.keys())
    terminals = set()
    for A in grammar:
        for rule in grammar[A]:
            for sym in rule:
                if sym not in nonterminals and sym != "ε":
                    terminals.add(sym)
    
    # я добавил для удобства в конце $ 
    terminals.add('$')
    
    # тут нужно собрать все правила в удобную форму (A -> a)
    all_productions = []
    for A in grammar:
        for rule in grammar[A]:
            all_productions.append((A, rule))
    # для каждого состояния
    for state_idx, items_set in enumerate(states):
        for item in items_set:
            if item.dot_pos < len(item.right):
                sym = item.right[item.dot_pos]
                # если это терминал, то ACTION[state_idx, sym] = shift
                if sym in terminals:
                    next_states = transitions.get((state_idx, sym), [])
                    for ns in next_states:
                        action_table[state_idx][sym].append(('s', ns))
                else:
                    next_states = transitions.get((state_idx, sym), [])
                    for ns in next_states:
                        goto_table[state_idx][sym].append(ns)
            else:
                if item.left == augmented_start and item.dot_pos == len(item.right):
                    action_table[state_idx]['$'].append(('acc', None))
                else:
                    for t in terminals:
                        action_table[state_idx][t].append(('r', (item.left, item.right)))
    
    return dict(action_table), dict(goto_table)


def lr0_parse(string, action_table, goto_table, states, grammar, start_symbol, augmented_start):
    tokens = list(string)
    tokens.append('$')

    start_stack = (tuple([0]), 0)  
    stack_queue = [start_stack]
    visited = set([start_stack])

    while stack_queue:
        state_stack, pos = stack_queue.pop()
        current_state = state_stack[-1]
        
        if pos >= len(tokens):
            continue
        lookahead = tokens[pos]
        
        actions = action_table.get(current_state, {}).get(lookahead, [])
        if not actions:
            continue
        
        for act_type, act_value in actions:
            if act_type == 's':
                new_stack = tuple(list(state_stack) + [act_value])
                new_conf = (new_stack, pos+1)
                if new_conf not in visited:
                    visited.add(new_conf)
                    stack_queue.append(new_conf)
            
            elif act_type == 'r':  
                A, rule = act_value
                length = 0 if rule == ["ε"] else len(rule)
                new_stack = state_stack[:-length]
                prev_state = new_stack[-1]
                goto_states = goto_table.get(prev_state, {}).get(A, [])
                for g_st in goto_states:
                    next_stack = tuple(list(new_stack) + [g_st])
                    new_conf = (next_stack, pos)
                    if new_conf not in visited:
                        visited.add(new_conf)
                        stack_queue.append(new_conf)
            
            elif act_type == 'acc':
                return True
    
    return False


# небольшие тесты 

# чтение файлов 

with open("grammar.txt", "r", encoding="utf-8") as file:
    grammar = [line.strip() for line in file if line.strip()]

print("Заданная грамматика:")
print(grammar)

grammar1, start_symbol = parse_grammar(grammar)

print("Преобразованная грамматика:")
print(grammar1)
print("Стартовый символ: ", start_symbol)

# удаление правил!

grammar1, start_symbol = remove_rules(grammar1, start_symbol)

print("После удаления правил: ")
print(grammar1)
print("Стартовый символ: ", start_symbol)


# построение PDA на основе LR(0)

states1, transitions1, aug_start1 = build_lr0_automaton(grammar1, start_symbol)

action_table_2, goto_table_2 = build_lr0_parse_table(states1, transitions1, grammar1, aug_start1)

print("\n=== Состояния LR(0) для грамматики  ===")
for i, st in enumerate(states1):
    print(f"I{i}:")
    for it in st:
        print("   ", it)
    print()

# запись в файл 
with open("transitions.txt", "w", encoding="utf-8") as file:
    file.write("\n=== Состояния PDA на основе LR(0) для грамматики ===\n")
    for i, st in enumerate(states1):
        file.write(f"I{i}:\n")
        for it in st:
            file.write(f"    {it}\n")
        file.write("\n")

# тестовые строчки: 


with open("test_strings.txt", "r", encoding="utf-8") as file:
    test_data = [line.strip().split() for line in file if line.strip()]
    test_strings = [(data[0], int(data[1])) for data in test_data]

print(test_strings)

OK = True
results = []

for string, result in test_strings:
    check = lr0_parse(string, action_table_2, goto_table_2, states1, grammar1, start_symbol, aug_start1)
    check = int(check)
    print(f"Тестовая строка '{string}' -> {check}")
    results.append(f"{string} {check}")
    check if check else 0
    if check != result:
        OK = False
    
print("ВСЁ ОК" if OK else "ОШИБКА")

# запись результата в файл

with open("results.txt", "w", encoding="utf-8") as file:
    file.write("\n".join(results) + "\n")
