# Enhanced Artisan Command System

This document outlines the comprehensive improvements made to the Laravel-style Artisan command system, bringing it much closer to Laravel's functionality while maintaining FastAPI compatibility.

## 🚀 Major Improvements

### 1. **Enhanced Command Base Class**

The `Command` base class now includes all major Laravel Artisan features:

#### **Laravel-Style Signature Parsing**
```python
class MyCommand(Command):
    signature = "mail:send {user : The user to send mail to} {--queue=default : Queue name} {--force : Force send}"
    description = "Send mail to a user"
```

#### **Interactive User Input**
- `ask()` - Prompt for input with validation
- `confirm()` - Yes/no questions  
- `choice()` - Multiple choice with support for multiple selections
- `secret()` - Hidden password input
- `anticipate()` - Auto-completion suggestions

#### **Rich Output Methods**
- `info()`, `comment()`, `warn()`, `error()` - Colored output
- `table()` - Formatted table display
- `progress_bar()` - Manual progress bars
- `with_progress_bar()` - Automated progress for collections
- `new_line()` - Line spacing control

#### **Advanced Features**
- `trap()` - Signal handling for graceful shutdown
- `call()` / `call_silently()` - Execute other commands
- `fail()` - Exit with custom error codes
- Verbosity levels (quiet, normal, verbose, very verbose, debug)

### 2. **Automatic Command Discovery**

The system now automatically discovers and registers commands:

```python
# Commands in app/Console/Commands/ are auto-discovered
# No manual registration required!
```

### 3. **Flexible Command Registration**

Multiple ways to define commands:

#### **Class-Based Commands**
```python
class EmailCommand(Command):
    signature = "email:send {recipient} {--subject=}"
    description = "Send an email"
    
    async def handle(self):
        recipient = self.argument("recipient")
        subject = self.option("subject", "Default Subject")
        # Send email logic
```

#### **Closure-Based Commands**
```python
from app.Console.Kernel import artisan

@artisan.command("inspire", description="Display inspiring quote")
async def inspire_command(cmd):
    cmd.info("Be yourself; everyone else is already taken. - Oscar Wilde")
```

### 4. **Comprehensive Scheduling System**

Laravel-style command scheduling with full cron support:

#### **Fluent Scheduling API**
```python
from app.Console.Scheduling import schedule

# Daily reports at 8:00 AM
schedule.command('reports:daily') \\
    .daily_at('8:00') \\
    .description('Send daily reports') \\
    .email_output_on_failure('admin@example.com')

# Cleanup every hour without overlapping
schedule.command('cleanup:temp') \\
    .hourly() \\
    .without_overlapping() \\
    .run_in_background()

# Conditional scheduling
schedule.command('backup:database') \\
    .daily_at('2:00') \\
    .when(lambda: is_production()) \\
    .weekdays()
```

#### **Advanced Scheduling Features**
- Time-based conditions (`between()`, `unless_between()`)
- Day-based scheduling (`weekdays()`, `weekends()`, `mondays()`, etc.)
- Conditional execution (`when()`, `skip()`)
- Overlap prevention (`without_overlapping()`)
- Background execution (`run_in_background()`)
- Output management (`send_output_to()`, `email_output_to()`)
- Before/after callbacks (`before()`, `after()`)

### 5. **Built-in Schedule Management Commands**

```bash
# Run due scheduled commands
python artisan.py schedule:run

# List all scheduled commands
python artisan.py schedule:list

# Start continuous schedule worker
python artisan.py schedule:work

# Test specific scheduled command
python artisan.py schedule:test command:name

# Clear schedule cache and locks
python artisan.py schedule:clear-cache
```

### 6. **Enhanced Argument and Option Parsing**

Full Laravel signature syntax support:

```python
# Required argument
"command {user}"

# Optional argument with default
"command {user=john}"

# Array arguments
"command {users*}"

# Optional array arguments
"command {users?*}"

# Options with values
"command {--queue=default}"

# Boolean options
"command {--force}"

# Array options
"command {--id=*}"

# Option shortcuts
"command {--Q|queue}"

# With descriptions
"command {user : The user ID} {--force : Force the action}"
```

### 7. **Code Generation Commands**

Enhanced make commands for generating boilerplate:

```bash
# Generate controller with resource methods
python artisan.py make:controller UserController --resource

# Generate custom Artisan command
python artisan.py make:command SendEmailCommand
```

### 8. **Comprehensive Example Commands**

The system includes extensive examples demonstrating all features:

- `example:greet` - Basic arguments and options
- `example:interactive` - User interaction methods
- `example:progress` - Progress bar usage
- `example:table` - Table output formatting
- `example:signals` - Signal handling
- `example:call` - Calling other commands
- `example:validate` - Input validation
- `example:errors` - Error handling patterns
- `example:long-running` - Background processes

## 📁 File Structure

```
app/Console/
├── Command.py              # Enhanced base command class
├── Kernel.py               # Artisan kernel with discovery
├── MakeControllerCommand.py # Updated controller generator
├── schedule.py             # Schedule configuration
├── Scheduling/
│   ├── __init__.py
│   └── Schedule.py         # Full scheduling system
└── Commands/
    ├── __init__.py
    ├── ExampleCommands.py  # Comprehensive examples
    ├── MakeCommandCommand.py # Command generator
    ├── MigrationCommands.py # Migration commands (existing)
    └── ScheduleCommands.py # Schedule management
```

## 🎯 Usage Examples

### Basic Command Usage
```bash
# List all commands
python artisan.py list

# Get help for specific command
python artisan.py help make:controller

# Run commands with arguments and options
python artisan.py example:greet "John Doe" --shout --repeat=3
```

### Using Make Commands
```bash
# Make a simple controller
make make-controller NAME=ApiController

# Make a resource controller
make make-controller NAME=UserController RESOURCE=1

# Make a custom command
make make-command NAME=ProcessPayments
```

### Schedule Management
```bash
# Run scheduled commands (typically in cron)
make schedule-run

# View all scheduled commands
make schedule-list

# Start schedule worker for development
make schedule-work
```

## 🔧 Integration with Makefile

The Makefile has been updated with convenient shortcuts:

```makefile
# Artisan command shortcuts
make artisan                    # List commands
make schedule-run              # Run due commands  
make make-controller NAME=Foo  # Generate controller
make example-greet             # Run example
```

## ⚡ Performance and Reliability

### Robust Error Handling
- Commands that fail to import are gracefully skipped
- Database dependency issues don't break command discovery
- Comprehensive exception handling throughout

### Signal Handling
- Graceful shutdown on SIGTERM/SIGINT
- Custom signal handlers per command
- Proper cleanup on interruption

### Command Isolation
- Prevent overlapping executions
- Mutex-based locking system
- Stale lock cleanup

## 🎨 Output Formatting

Rich console output with:
- ✅ Colored success messages
- ⚠️ Warning indicators  
- ❌ Error highlighting
- 💬 Informational comments
- 📊 Formatted tables
- 📈 Progress bars with percentages

## 🔄 Migration Path

All existing commands remain functional - the improvements are fully backward compatible while adding powerful new capabilities.

## 📚 Next Steps

The command system now provides a solid foundation for:
- Complex data processing workflows
- Automated maintenance tasks
- Development tooling
- CI/CD pipeline integration
- Background job processing
- System monitoring and alerts

This enhanced system brings the FastAPI Laravel project's command-line interface to true Laravel parity while maintaining Python idioms and async support.