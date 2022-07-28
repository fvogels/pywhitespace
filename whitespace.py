def sanitize(instructions):
    return "".join(instruction for instruction in instructions if instruction in " \t\n")

class Instruction:
    def perform(self, vm):
        self._perform(vm)
        vm.instruction_index += 1

class Nullary(Instruction):
    def __str__(self):
        return f'{type(self).__name__}'

    def __repr__(self):
        return str(self)

class Unary(Instruction):
    def __init__(self, argument):
        self.argument = argument

    def __str__(self):
        return f'{type(self).__name__}({repr(self.argument)})'

    def __repr__(self):
        return str(self)

class Duplicate(Nullary):
    def _perform(self, vm):
        vm.stack.append(vm.stack[-1])

class Swap(Nullary):
    def _perform(self, vm):
        a = vm.stack.pop()
        b = vm.stack.pop()
        vm.stack.append(a)
        vm.stack.append(b)

class Discard(Nullary):
    def _perform(self, vm):
        vm.stack.pop()

class BinArith(Nullary):
    def _perform(self, vm):
        a = vm.stack.pop()
        b = vm.stack.pop()
        vm.stack.append(self._combine(a, b))

class Add(BinArith):
    def _combine(self, a, b):
        return b + a

class Subtract(BinArith):
    def _combine(self, a, b):
        return b - a

class Multiply(BinArith):
    def _combine(self, a, b):
        return b * a

class Division(BinArith):
    def _combine(self, a, b):
        if a == 0:
            raise RuntimeError()
        return b // a

class Modulo(BinArith):
    def _combine(self, a, b):
        if a == 0:
            raise RuntimeError()
        return b % a

class Store(Nullary):
    def _perform(self, vm):
        a = vm.stack.pop()
        b = vm.stack.pop()
        vm.heap[b] = a

class Retrieve(Nullary):
    def _perform(self, vm):
        a = vm.stack.pop()
        vm.stack.append(vm.heap[a])

class ReadChar(Nullary):
    def _perform(self, vm):
        char = vm.input[vm.input_index]
        vm.input_index += 1
        address = vm.stack.pop()
        vm.heap[address] = ord(char)

class ReadNumber(Nullary):
    def _perform(self, vm):
        string = ''
        while (char := vm.input[vm.input_index]) != "\n":
            string += char
            vm.input_index += 1
        vm.input_index += 1
        address = vm.stack.pop()
        vm.heap[address] = int(string)

class WriteChar(Nullary):
    def _perform(self, vm):
        vm.output += chr(vm.stack.pop())

class WriteNumber(Nullary):
    def _perform(self, vm):
        vm.output += str(vm.stack.pop())

class Return(Nullary):
    def perform(self, vm):
        vm.instruction_index = vm.call_stack.pop()

class Exit(Nullary):
    def perform(self, vm):
        vm.stop()

class Push(Unary):
    def _perform(self, vm):
        vm.stack.append(self.argument)

class Copy(Unary):
    def _perform(self, vm):
        if self.argument < 0:
            raise RuntimeError()
        vm.stack.append(vm.stack[-self.argument-1])

class Slide(Unary):
    def _perform(self, vm):
        a = vm.stack.pop()
        if self.argument < 0:
            n = len(vm.stack)
        else:
            n = min(len(vm.stack), self.argument)
        vm.stack = vm.stack[:-n]
        vm.stack.append(a)

class Label(Unary): pass

class Call(Unary):
    def perform(self, vm):
        vm.call_stack.append(vm.instruction_index + 1)
        vm.instruction_index = vm.label_table[self.argument]

class Jump(Unary):
    def perform(self, vm):
        vm.instruction_index = vm.label_table[self.argument]

class JumpIfZero(Unary):
    def perform(self, vm):
        if vm.stack.pop() == 0:
            vm.instruction_index = vm.label_table[self.argument]
        else:
            vm.instruction_index += 1

class JumpIfNegative(Unary):
    def perform(self, vm):
        if vm.stack.pop() < 0:
            vm.instruction_index = vm.label_table[self.argument]
        else:
            vm.instruction_index += 1

def tokenize(instructions):
    def next():
        nonlocal index
        result = instructions[index]
        index += 1
        return result

    def matches(prefix):
        nonlocal index
        if instructions[index:index+len(prefix)] == prefix:
            index += len(prefix)
            return True
        else:
            return False

    def number():
        sign = 1 if next() == ' ' else -1
        value = 0
        while (current := next()) != '\n':
            value = value * 2 + (0 if current == ' ' else 1)
        return sign * value

    def label():
        result = ''
        while (current := next()) != '\n':
            result += current
        return result

    index = 0

    while index < len(instructions):
        if matches('  '): yield Push(number())
        elif matches(' \n '): yield Duplicate()
        elif matches(' \t '): yield Copy(number())
        elif matches(' \n\t'): yield Swap()
        elif matches(' \n\n'): yield Discard()
        elif matches(' \t\n'): yield Slide(number())
        elif matches('\t   '): yield Add()
        elif matches('\t  \t'): yield Subtract()
        elif matches('\t  \n'): yield Multiply()
        elif matches('\t \t '): yield Division()
        elif matches('\t \t\t'): yield Modulo()
        elif matches('\t\t '): yield Store()
        elif matches('\t\t\t'): yield Retrieve()
        elif matches('\n  '): yield Label(label())
        elif matches('\n \t'): yield Call(label())
        elif matches('\n \n'): yield Jump(label())
        elif matches('\n\t '): yield JumpIfZero(label())
        elif matches('\n\t\t'): yield JumpIfNegative(label())
        elif matches('\n\t\n'): yield Return()
        elif matches('\n\n\n'): yield Exit()
        elif matches('\t\n  '): yield WriteChar()
        elif matches('\t\n \t'): yield WriteNumber()
        elif matches('\t\n\t '): yield ReadChar()
        elif matches('\t\n\t\t'): yield ReadNumber()
        else: raise RuntimeError(f'Unrecognized token: {repr(instructions[index:])}')

class VirtualMachine:
    def __init__(self, instructions, label_table, input):
        self.instructions = instructions
        self.label_table = label_table
        self.input = input
        self.input_index = 0
        self.instruction_index = 0
        self.call_stack = []
        self.stack = []
        self.heap = {}
        self.output = ''
        self.running = True

    def step(self):
        self.current_instruction.perform(self)

    def run(self):
        steps = 100
        while self.running and steps > 0:
            self.step()
            steps -= 1

    def stop(self):
        self.running = False

    @property
    def current_instruction(self):
        return self.instructions[self.instruction_index]

def parse(tokens):
    instructions = []
    table = {}
    for token in tokens:
        if isinstance(token, Label):
            if token.argument in table:
                raise RuntimeError()
            table[token.argument] = len(instructions)
        else:
            instructions.append(token)
    return (instructions, table)

def whitespace(code, input=''):
    tokens = tokenize(sanitize(code))
    instructions, label_table = parse(tokens)
    vm = VirtualMachine(instructions, label_table, input)
    vm.run()
    return vm.output



programs = [
    # ("   \t\n\t\n \t\n\n\n", ''),
    # ("   \t \n\t\n \t\n\n\n", ''),
    # ("   \t\t\n\t\n \t\n\n\n", ''),
    # ("    \n\t\n \t\n\n\n", ''),
    # ("  \t\t\n\t\n \t\n\n\n", ''),
    # ("  \t\t \n\t\n \t\n\n\n", ''),
    # ("  \t\t\t\n\t\n \t\n\n\n", ''),
    # ("   \t     \t\n\t\n  \n\n\n", ''),
    # ("   \t    \t \n\t\n  \n\n\n", ''),
    # ("   \t    \t\t\n\t\n  \n\n\n", ''),
    # ('blahhhh   \targgggghhh     \t\n\t\n  \n\n\n', ''),
    # ('   \t\n   \t \n   \t\t\n \t  \t \n\t\n \t\n\n\n', ''),
    # ('   \t\n   \t \n   \t\t\n \t  \t\n\t\n \t\n\n\n', ''),
    # ('   \t\n   \t \n   \t\t\n \t   \n\t\n \t\n\n\n', ''),
    # ('   \t\n   \t \n   \t\t\n \t  \t\t\n\t\n \t\n\n\n', ''),
    # ('   \t\n   \t \n   \t\t\n \t\n\t\t     \n\t\n \t\t\n \t\n\n\n', ''),
    # ('   \t\n\t\n\t\t   \t \n\t\n\t\t   \t\t\n\t\n\t\t   \t\t\n\t\t\t   \t \n\t\t\t   \t\n\t\t\t\t\n \t\t\n \t\t\n \t\n\n\n', '1\n2\n3\n'),
    # ('   \t\n   \t\t\n   \n   \t \n   \n   \t\n\n  \n\t\n \t\n\t \n\n\n\n', ''),
    # ('  \t\t\n   \n   \t\n   \t \n   \t\t\n\n  \n\t\n \t \n \n\t\t \n\n \n\n\n   \n\n\n\n', ''),
    # ('   \t\n   \t \n   \t\t\n\t\n \t\n \n\n\t\n \t\t\n \t\n  \n\n  \n\n\n\n', ''),
    ('   \t\n \n  \n \t\t  \t\t\t\n\n\n', ''),
]


for program, input in programs:
    print(whitespace(program, input))
