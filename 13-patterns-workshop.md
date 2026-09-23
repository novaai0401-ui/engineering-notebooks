# Notebook 13 — All 23 classic design patterns, implemented and challenged

A pattern is a reusable way to arrange responsibilities. It is not a medal for adding more classes. Each example below is a complete small implementation of the pattern's mechanism with an executable assertion. The examples use Python to keep the mechanism visible; the design roles also apply to Java. Production versions need the surrounding validation, concurrency and resource management appropriate to their domain.

For each pattern, learn four things: the problem, the cooperating roles, a simpler alternative, and the cost. Explain those before naming the pattern in an interview. The 23 patterns here are the classic GoF catalog, not every design pattern ever described.

## 1. Factory Method — subclasses choose the product

A delivery workflow knows it needs a transport but lets a subclass choose the transport implementation. The creator's workflow calls an overridable creation method. This differs from merely putting an `if` statement in a factory function. Use it when extending a framework through subclasses is already appropriate. A constructor parameter or ordinary factory function is often simpler when inheritance buys nothing.

```python
# lab: pattern_factory_method
from abc import ABC, abstractmethod
class Delivery(ABC):
    @abstractmethod
    def transport(self): ...
    def deliver(self,parcel):return self.transport().carry(parcel)
class Bicycle:
    def carry(self,parcel):return f'bike:{parcel}'
class LocalDelivery(Delivery):
    def transport(self):return Bicycle()
assert LocalDelivery().deliver('book')=='bike:book'
print('Creator workflow uses the subclass-created product')
```

**Failure mode:** one subclass per trivial parameter creates needless hierarchy. **Test idea:** supply a different creator and confirm the shared workflow remains unchanged.

## 2. Abstract Factory — create compatible families

A classroom screen needs both a button and a notice. A family factory creates matching variants so a client does not accidentally mix incompatible families. Use this when several related products must vary together. A theme configuration is simpler when only colors vary; do not create object families for every cosmetic value.

```python
# lab: pattern_abstract_factory
class QuietButton:
    def render(self):return 'quiet button'
class QuietNotice:
    def render(self):return 'quiet notice'
class BrightButton:
    def render(self):return 'bright button'
class BrightNotice:
    def render(self):return 'bright notice'
class QuietFactory:
    def button(self):return QuietButton()
    def notice(self):return QuietNotice()
class BrightFactory:
    def button(self):return BrightButton()
    def notice(self):return BrightNotice()
def screen(factory):return (factory.button().render(),factory.notice().render())
assert screen(QuietFactory())==('quiet button','quiet notice')
assert screen(BrightFactory())==('bright button','bright notice')
print('Each factory supplies a consistent product family')
```

**Cost:** adding a new product kind requires changing every factory. Adding a new family is easier. That asymmetry should match the changes you expect.

## 3. Builder — construct a valid object step by step

A builder accumulates construction choices and validates them at the final boundary. The resulting object should not share accidental mutable construction state. Use this for many optional fields or staged construction. For two required arguments, a constructor is clearer. A fluent API alone does not necessarily implement a meaningful builder.

```python
# lab: pattern_builder_complete
from dataclasses import dataclass
@dataclass(frozen=True)
class StudyPlan:
    title:str
    topics:tuple[str,...]
class PlanBuilder:
    def __init__(self,title):self.title=title;self.topics=[]
    def add(self,topic):self.topics.append(topic);return self
    def build(self):
        if not self.title.strip() or not self.topics:raise ValueError('title and topics required')
        return StudyPlan(self.title,tuple(self.topics))
builder=PlanBuilder('Interview').add('graphs')
plan=builder.build();builder.add('SQL')
assert plan.topics==('graphs',)
try:PlanBuilder('').build()
except ValueError:pass
else:raise AssertionError('invalid plan accepted')
print('Built values are validated and independent of later builder changes')
```

## 4. Prototype — copy a configured example

Instead of reconstructing a complex configuration from scratch, clone a prototype. Decide which members are copied deeply and which represent shared external resources. A deep copy of a database connection is not a meaningful new connection. Prefer explicit constructors when they make ownership clearer.

```python
# lab: pattern_prototype
from copy import deepcopy
class ExerciseTemplate:
    def __init__(self,title,hints):self.title=title;self.hints=hints
    def clone(self):return deepcopy(self)
original=ExerciseTemplate('BFS',['use a queue'])
copy=original.clone();copy.hints.append('mark visited when enqueued')
assert original.hints==['use a queue'] and len(copy.hints)==2
print('Prototype clone does not share its mutable hint list')
```

**Cost:** implicit copying rules can hide expensive work or copy inappropriate identity fields. Test nested mutation, not only equality immediately after cloning.

## 5. Singleton — one instance within a defined boundary

This pattern restricts construction and exposes one instance. Define the boundary: one Python class in one process is not one instance across a distributed system. Shared mutable state complicates tests and concurrency. Dependency injection of one ordinary object is often preferable because dependencies remain visible.

```python
# lab: pattern_singleton
import threading
class ProcessRegistry:
    _instance=None
    _lock=threading.Lock()
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:cls._instance=super().__new__(cls)
            return cls._instance
first=ProcessRegistry();second=ProcessRegistry()
assert first is second
print('Construction is serialized and returns one process-local instance')
```

The lock protects instance creation, not every future operation on it. Avoid mutable initialization that reruns on every constructor call. Serialization, subclassing and multiple processes require separate design decisions.

## 6. Adapter — translate an incompatible interface

A legacy API reports temperature in Fahrenheit while the new client expects Celsius. The adapter translates the interface and semantics without modifying the legacy component. A plain conversion function is sufficient for one isolated call; an adapter object helps when integrating a larger stable interface.

```python
# lab: pattern_adapter_complete
class LegacyThermometer:
    def fahrenheit(self):return 68
class CelsiusAdapter:
    def __init__(self,legacy):self.legacy=legacy
    def read(self):return (self.legacy.fahrenheit()-32)*5/9
assert CelsiusAdapter(LegacyThermometer()).read()==20
print('Adapter translates both method shape and units')
```

**Failure mode:** forwarding methods while forgetting units, error semantics or ownership. The tests should assert meaning, not just that a method was called.

## 7. Bridge — vary abstraction and implementation independently

A report has a high-level purpose; its output device is a separate choice. The bridge lets report types and renderers vary without creating every report-renderer subclass combination. If only one axis changes, simple composition without a named hierarchy may be enough.

```python
# lab: pattern_bridge
class PlainRenderer:
    def render(self,title):return title
class BracketRenderer:
    def render(self,title):return '['+title+']'
class Report:
    def __init__(self,renderer):self.renderer=renderer
    def output(self):return self.renderer.render('Study report')
class DetailedReport(Report):
    def output(self):return self.renderer.render('Detailed study report')
assert Report(PlainRenderer()).output()=='Study report'
assert DetailedReport(BracketRenderer()).output()=='[Detailed study report]'
print('Report kind and rendering implementation vary independently')
```

**Cost:** premature separation creates abstractions with only one trivial implementation. Identify actual independent variation first.

## 8. Composite — treat a tree uniformly

A lesson takes a number of minutes; a module contains lessons or other modules and sums their times. Both answer the same operation. Use a composite when a recursive whole-part structure is natural. Do not force leaf-only operations onto containers without defining meaningful behavior.

```python
# lab: pattern_composite
class LessonPart:
    def __init__(self,duration):self.duration=duration
    def minutes(self):return self.duration
class ModulePart:
    def __init__(self,*children):self.children=children
    def minutes(self):return sum(child.minutes() for child in self.children)
course=ModulePart(LessonPart(10),ModulePart(LessonPart(20),LessonPart(5)))
assert course.minutes()==35 and ModulePart().minutes()==0
print('The same operation works on leaves and nested groups')
```

Cycles would destroy the tree assumption and can cause infinite recursion. Enforce acyclicity or add cycle handling if arbitrary graphs are allowed.

## 9. Decorator — wrap behavior while preserving the interface

A reader returns text. One decorator uppercases it; another adds brackets. Each wrapper still behaves like a reader and can be composed. Decorator order matters. A direct function pipeline is simpler when there is no persistent object interface to preserve.

```python
# lab: pattern_decorator_complete
class TextReader:
    def read(self):return 'agents'
class UpperReader:
    def __init__(self,inner):self.inner=inner
    def read(self):return self.inner.read().upper()
class BracketReader:
    def __init__(self,inner):self.inner=inner
    def read(self):return '['+self.inner.read()+']'
assert BracketReader(UpperReader(TextReader())).read()=='[AGENTS]'
print('Wrappers add behavior while retaining the reader contract')
```

**Failure mode:** wrappers accidentally double-log, double-retry or change exception behavior. Test combinations, especially when a retry decorator wraps a side-effecting operation.

## 10. Facade — a simpler entry point to a subsystem

A study session requires loading a lesson and selecting a quiz. A facade presents one convenient operation while leaving the underlying components independently usable. It should simplify orchestration, not swallow every error or become the application's all-knowing object.

```python
# lab: pattern_facade
class LessonStore:
    def load(self,topic):return {'topic':topic,'text':'Explain '+topic}
class QuizStore:
    def choose(self,topic):return 'Why use '+topic+'?'
class ClassroomFacade:
    def __init__(self,lessons,quizzes):self.lessons=lessons;self.quizzes=quizzes
    def session(self,topic):return {'lesson':self.lessons.load(topic),'quiz':self.quizzes.choose(topic)}
session=ClassroomFacade(LessonStore(),QuizStore()).session('queues')
assert session['lesson']['topic']=='queues' and session['quiz']=='Why use queues?'
print('Facade coordinates a small subsystem through one use-case operation')
```

An application service may already play this role. Adding another facade on top of it without simplifying the contract is redundant.

## 11. Flyweight — share immutable intrinsic data

Many displayed characters can share one immutable style, while position remains separate. The factory reuses styles by value. Intrinsic state is shared; extrinsic state stays with each use. Use it when repeated immutable data materially consumes memory. A cache without a size or lifecycle policy can cost more than it saves.

```python
# lab: pattern_flyweight
from dataclasses import dataclass
@dataclass(frozen=True)
class GlyphStyle:
    font:str
    size:int
class StylePool:
    def __init__(self):self.styles={}
    def get(self,font,size):
        key=(font,size)
        if key not in self.styles:self.styles[key]=GlyphStyle(font,size)
        return self.styles[key]
pool=StylePool();a={'style':pool.get('serif',12),'x':0};b={'style':pool.get('serif',12),'x':10}
assert a['style'] is b['style'] and a['x']!=b['x']
print('Immutable style is shared; position is not')
```

Never share mutable user-specific data accidentally. Interning every unique string forever is not a general memory optimization.

## 12. Proxy — control access to another object

A proxy implements the same interface while deciding whether or when to contact the real object. It may enforce access, lazy-load, or represent a remote object. A proxy cannot make remote latency and failures disappear; callers still need an honest contract.

```python
# lab: pattern_proxy
class SecretStore:
    def read(self):return 'private lesson'
class PermissionProxy:
    def __init__(self,target,allowed):self.target=target;self.allowed=allowed
    def read(self):
        if not self.allowed:raise PermissionError('denied')
        return self.target.read()
assert PermissionProxy(SecretStore(),True).read()=='private lesson'
try:PermissionProxy(SecretStore(),False).read()
except PermissionError:pass
else:raise AssertionError('access bypassed')
print('Proxy enforces a check before delegation')
```

The boolean is deliberately supplied by test setup, not by an untrusted caller. Real authorization must derive it from authenticated identity and policy. If clients can bypass the proxy and call the object directly, the security boundary is ineffective.

## 13. Chain of Responsibility — pass a request through handlers

Each handler either processes a request or passes it onward. The terminal behavior must be explicit. Middleware pipelines often resemble this pattern, although some pipelines always execute every stage rather than stopping at the first handler. Use a straightforward conditional when there are only two stable cases.

```python
# lab: pattern_chain
class Handler:
    def __init__(self,predicate,action,next_handler=None):self.predicate=predicate;self.action=action;self.next=next_handler
    def handle(self,request):
        if self.predicate(request):return self.action(request)
        if self.next:return self.next.handle(request)
        raise ValueError('unhandled request')
large=Handler(lambda x:x>=10,lambda x:'large')
small=Handler(lambda x:0<=x<10,lambda x:'small',large)
assert small.handle(4)=='small' and small.handle(20)=='large'
try:small.handle(-1)
except ValueError:pass
else:raise AssertionError('unhandled request silently accepted')
print('A chain delegates until one handler accepts, or fails explicitly')
```

Handler order changes behavior. Authentication and authorization middleware must not be optional stages that an earlier success bypasses accidentally.

## 14. Command — turn a request into an object

A command captures the receiver and requested operation. An invoker can queue it, record it, or support undo. Undo is not always possible: an external email cannot be unsent merely by restoring local state. Prefer a plain function when commands do not need identity, history or lifecycle.

```python
# lab: pattern_command_complete
class Document:
    def __init__(self):self.text=''
class AppendCommand:
    def __init__(self,document,text):self.document=document;self.text=text;self.before=None
    def execute(self):
        if self.before is not None:raise ValueError('already executed')
        self.before=self.document.text;self.document.text+=self.text
    def undo(self):
        if self.before is None:raise ValueError('not executed')
        self.document.text=self.before;self.before=None
document=Document();command=AppendCommand(document,'hello')
command.execute();assert document.text=='hello';command.undo();assert document.text==''
print('Command captures an operation and restores its prior local state')
```

This undo assumes no intervening edits. Concurrent editing requires version checks or operation-aware transformations; blindly restoring a snapshot can erase someone else's work.

## 15. Interpreter — evaluate a small language

Represent an expression as a tree and define how each node evaluates. This is appropriate for a small, deliberately restricted language. Never substitute unrestricted `eval` for a safe interpreter of untrusted input. Large grammars usually deserve parser tools and a more systematic compiler design.

```python
# lab: pattern_interpreter
class Literal:
    def __init__(self,value):self.value=value
    def evaluate(self,context):return self.value
class Variable:
    def __init__(self,name):self.name=name
    def evaluate(self,context):return context[self.name]
class AddExpression:
    def __init__(self,left,right):self.left=left;self.right=right
    def evaluate(self,context):return self.left.evaluate(context)+self.right.evaluate(context)
expression=AddExpression(Variable('score'),Literal(2))
assert expression.evaluate({'score':8})==10
print('A restricted expression tree has explicit evaluation rules')
```

The example constructs the tree directly; it does not include a text parser. A network-facing interpreter needs input-size, depth, execution and resource limits.

## 16. Iterator — traverse without exposing representation

An iterator supplies one element at a time and tracks traversal state separately from the collection. Two iterators should be able to progress independently. Python generators provide a concise implementation; a custom class is unnecessary unless you need additional behavior.

```python
# lab: pattern_iterator
class LessonShelf:
    def __init__(self,lessons):self._lessons=tuple(lessons)
    def __iter__(self):
        for lesson in self._lessons:yield lesson
shelf=LessonShelf(['python','java']);a=iter(shelf);b=iter(shelf)
assert next(a)=='python' and next(a)=='java' and next(b)=='python'
assert list(shelf)==['python','java']
print('Traversal state belongs to each iterator, not the collection')
```

Define mutation semantics for mutable collections: snapshot, fail-fast, or weakly consistent traversal. Do not promise all three simultaneously.

## 17. Mediator — coordinate peers through one collaboration point

Instead of every participant knowing every other participant, a mediator routes collaboration. A classroom mediator forwards a question to a tutor and records the answer. It reduces peer coupling, but a giant mediator can become harder to maintain than the original network.

```python
# lab: pattern_mediator
class TutorParticipant:
    def answer(self,question):return 'Example for '+question
class LearnerParticipant:
    def __init__(self,mediator):self.mediator=mediator
    def ask(self,question):return self.mediator.ask(question)
class ClassroomMediator:
    def __init__(self,tutor):self.tutor=tutor;self.history=[]
    def ask(self,question):
        answer=self.tutor.answer(question);self.history.append((question,answer));return answer
mediator=ClassroomMediator(TutorParticipant());learner=LearnerParticipant(mediator)
assert learner.ask('BFS')=='Example for BFS' and len(mediator.history)==1
print('The learner delegates collaboration to a mediator')
```

A direct call is better when two components have one simple relationship. Add mediation for genuine coordination rules, not to hide every dependency.

## 18. Memento — capture and restore private state

The originator creates a snapshot; a caretaker stores it; restoration happens through the originator. This separates history management from editing logic. Python does not enforce deep privacy here, so immutable snapshots make the intended boundary clear. For large documents, full snapshots may be too expensive; commands or deltas are alternatives.

```python
# lab: pattern_memento
from dataclasses import dataclass
@dataclass(frozen=True)
class Snapshot:
    text:str
class Editor:
    def __init__(self):self._text=''
    def write(self,text):self._text=text
    def save(self):return Snapshot(self._text)
    def restore(self,snapshot):self._text=snapshot.text
    def read(self):return self._text
editor=Editor();editor.write('first');history=[editor.save()]
editor.write('second');editor.restore(history.pop());assert editor.read()=='first'
print('Caretaker stores a snapshot without implementing restoration')
```

As with command undo, restoring old state can conflict with concurrent changes. Persisted snapshots also need schema-version handling.

## 19. Observer — notify subscribers of a change

A subject maintains subscriptions and notifies observers. The subject does not need to know each observer's purpose. Manage subscription lifetime so old screens and objects do not stay reachable forever. A direct call is clearer for one mandatory collaborator whose failure must abort the operation.

```python
# lab: pattern_observer_complete
class Scores:
    def __init__(self):self.listeners=[]
    def subscribe(self,listener):
        self.listeners.append(listener)
        def unsubscribe():
            if listener in self.listeners:self.listeners.remove(listener)
        return unsubscribe
    def publish(self,score):
        for listener in tuple(self.listeners):listener(score)
subject=Scores();seen=[];stop=subject.subscribe(seen.append)
subject.publish(7);stop();stop();subject.publish(9)
assert seen==[7]
print('Subscribers receive changes and can unsubscribe idempotently')
```

This implementation propagates listener errors and stops later notifications. That is an explicit policy, not a universal observer guarantee. Async observers introduce ordering, backpressure and delivery questions similar to messaging.

## 20. State — behavior changes with lifecycle state

A job behaves differently while waiting, running and completed. State objects encapsulate allowed transitions. A transition table is often simpler for a small finite lifecycle; state objects help when each state has substantial behavior. Invalid transitions should fail visibly rather than silently mutate the object.

```python
# lab: pattern_state_complete
class Waiting:
    def approve(self,job):job.state=Running()
    def finish(self,job):raise ValueError('not running')
class Running:
    def approve(self,job):raise ValueError('already running')
    def finish(self,job):job.state=Finished()
class Finished:
    def approve(self,job):raise ValueError('terminal')
    def finish(self,job):raise ValueError('terminal')
class StatefulJob:
    def __init__(self):self.state=Waiting()
    def approve(self):self.state.approve(self)
    def finish(self):self.state.finish(self)
job=StatefulJob();job.approve();job.finish();assert isinstance(job.state,Finished)
try:job.approve()
except ValueError:pass
else:raise AssertionError('terminal transition accepted')
print('State objects own transition behavior')
```

For persisted concurrent jobs, an in-memory state class is not enough. Enforce transitions with conditional database updates or appropriate transactions too.

## 21. Strategy — select an interchangeable algorithm

A strategy changes how a task is performed while preserving its contract. A scorer can use mean or minimum aggregation without changing the report. Python functions are often the simplest strategies; Java may use a functional interface. Avoid a class hierarchy if a function parameter clearly expresses the variation.

```python
# lab: pattern_strategy_complete
def mean_score(values):return sum(values)/len(values)
def strict_score(values):return min(values)
class Assessment:
    def __init__(self,strategy):self.strategy=strategy
    def grade(self,values):
        if not values:raise ValueError('scores required')
        return self.strategy(values)
assert Assessment(mean_score).grade([6,10])==8
assert Assessment(strict_score).grade([6,10])==6
print('The same assessment workflow selects different grading algorithms')
```

Strategies must honor shared expectations about input, output and side effects. Swapping in a strategy with different units or mutation behavior breaks substitutability.

## 22. Template Method — fix the skeleton, vary selected steps

A training pipeline fixes the order load → transform → summarize, while subclasses customize a step. Factory Method customizes creation; Template Method customizes steps of an algorithm. Composition with function arguments is often easier to combine and test than deep inheritance.

```python
# lab: pattern_template_method
from abc import ABC,abstractmethod
class Pipeline(ABC):
    def run(self,values):
        clean=self.transform(values)
        return sum(clean)
    @abstractmethod
    def transform(self,values):...
class PositivePipeline(Pipeline):
    def transform(self,values):return [value for value in values if value>0]
assert PositivePipeline().run([-2,3,4])==7
print('The pipeline skeleton delegates one variable step')
```

Too many hooks make the skeleton impossible to reason about. Document when hooks run and which invariants subclasses must preserve.

## 23. Visitor — add operations to a stable object structure

Objects accept a visitor, which implements an operation for each concrete element type. This makes adding new operations easier when element types are stable. Adding a new element type requires updating visitors, so the tradeoff is the opposite of some inheritance designs.

```python
# lab: pattern_visitor
class VideoLesson:
    def __init__(self,minutes):self.minutes=minutes
    def accept(self,visitor):return visitor.video(self)
class ReadingLesson:
    def __init__(self,words):self.words=words
    def accept(self,visitor):return visitor.reading(self)
class TimeVisitor:
    def video(self,lesson):return lesson.minutes
    def reading(self,lesson):return lesson.words/200
class KindVisitor:
    def video(self,lesson):return 'video'
    def reading(self,lesson):return 'reading'
elements=[VideoLesson(10),ReadingLesson(1000)]
assert sum(item.accept(TimeVisitor()) for item in elements)==15
assert [item.accept(KindVisitor()) for item in elements]==['video','reading']
print('Two operations traverse the same stable element types')
```

The reading speed is a teaching assumption, not a universal measurement. Alternatives include pattern matching, ordinary polymorphic methods, or functions over tagged data. Choose according to which axis changes most often.

## 24. Distinguish patterns that look similar

Adapter changes the interface; decorator preserves it while adding behavior; proxy preserves it while controlling access. Bridge separates independent dimensions before combinations multiply. Facade simplifies a subsystem; mediator coordinates peers. Strategy chooses an algorithm; state reflects lifecycle-dependent behavior. Command captures an operation; memento captures state. A class may participate in more than one pattern, but naming patterns does not prove a design is good.

## 25. Pattern interview and design challenge

**Task, 20 points:** Design a study-report generator with two output formats, multiple scoring rules, undo for local drafts, and authenticated publication. Award 4 points for clear responsibilities, 4 for suitable composition, 4 for correct undo limitations, 4 for server-side authorization and idempotency, and 4 for tests and a simpler alternative. Do not require a pattern name if the design solves the problem clearly.

**Answer sketch:** Inject a formatter and scoring strategy into an application service. Use snapshots or commands for draft history with explicit version checks. Put publication behind an authenticated service boundary, persist an operation key and return a stable result. A facade may simplify the use case; a singleton is unnecessary. Do not build 23 patterns into one application to prove you know them.

**Mastery exercise:** For each cell, modify one assertion to describe an invalid use, then decide whether the implementation should reject it or the contract should exclude it. Add the appropriate check. Explain one situation where deleting the pattern would improve the code.
