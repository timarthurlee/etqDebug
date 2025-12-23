import inspect
class EtqDebug(object):
    LEVEL_ORDER = ['debug', 'info', 'warn', 'error', 'none']
    LEVEL_MAP = {
        'debug': {'display': 'DEBUG', 'aliases': ['debug']},
        'info': {'display': 'INFO', 'aliases': ['info', 'information']},
        'warn': {'display': 'WARN', 'aliases': ['warn', 'warning']},
        'error': {'display': 'ERROR', 'aliases': ['error']},
        'none': {'display': 'NONE', 'aliases': ['none', 'off', 'disabled']}
    }     
    def __init__(self, label=None, minLevel=None, document=None):              
        env = engineConfig.getEnvironmentName()        
        isProd = env.lower() in ['production', 'prod']
        
        # Default minimum level (e.g., from config)
        if minLevel is None:
            minLevel = 'debug' if (not isProd or thisUser.isMember('ADMINISTRATORS',None)) else 'error'

        self.setMinLevel(minLevel)

        self._document = thisDocument if document is None else document

        if not label:
            if self._document is not None:
                formName = self._document.getFormName()
                applicationName = self._document.getParentApplication().getName()
                label = '{} - {} #{}'.format(applicationName, formName, '{ETQ$NUMBER}')
        self._label = self._getFieldsInString(label)    
    
    def setMinLevel(self, level):
        """Set the minimum logging level."""
        self._minLevel = self._normalizeLevel(level)

    def _normalizeLevel(self, level):
        """Convert 'information' → 'info', return canonical level"""
        level = level.lower()
        for canonical, info in self.LEVEL_MAP.items():
            if level in info['aliases']:
                return canonical
        return 'debug'  # default
    
    def _getLevelIndex(self, level):
        """Get numeric index for level comparison."""
        canonical = self._normalizeLevel(level)
        try:
            return self.LEVEL_ORDER.index(canonical)
        except ValueError:
            return 0  # default to debug
        
    def _shouldLog(self, level):
        """
        Determine if a log message at the given level should be emitted.
        """
        if self._minLevel == 'none':
            return False  # Special case: nothing logs
        
        callerIdx = self._getLevelIndex(level)
        minIdx = self._getLevelIndex(self._minLevel)
        return callerIdx >= minIdx

    def _toUnicode(self, value, encoding='utf-8'):
        """Enhanced unicode conversion with better error handling"""
        if value is None:
            return u''
        if isinstance(value, unicode):
            return value
        if isinstance(value, str):
            # Try multiple encodings
            encodings = ['utf-8', 'latin1', 'cp1252', 'ascii']
            for enc in encodings:
                try:
                    return value.decode(enc)
                except UnicodeDecodeError:
                    continue
            # If all fail, use replacement characters but log it
            self.log('Unicode decode failed for: ' + repr(value), 'toUnicode')
            return value.decode('utf-8', 'replace')
        
        # Handle other types
        try:
            return unicode(str(value))
        except UnicodeDecodeError:
            self.log('Unicode conversion failed for type: ' + str(type(value)), 'toUnicode')
            return unicode(str(value), 'utf-8', 'replace')

    def _getField(self, fieldName, document=None, separator = ', '):
        output = ''
        document = document if document != None else self._document
        field = document.getField(fieldName)
        inputString = '{'+fieldName+'}'
        if field is None or field.getSetting() is None:
            self.log('Invalid fieldname provided.', 'getField:')
            return inputString       
        
        fieldSetting = field.getSetting()             
        if fieldSetting.getFieldType() in [fieldSetting.FIELD_TYPE_LINK]:
            links = field.getDocLinks()
            if not links:
                return 'No Links'
            output = separator.join(links.getDescription(field.getLocale(), thisUser.getTimeZone()))
        elif fieldSetting.getFieldType() not in [fieldSetting.FIELD_TYPE_ATTACHMENT]:
            #if fieldSetting.isMultiValue():
            #    output = separator.join(field.getEncodedTextList())
            #else:
            output = field.getEncodedDisplayText()

        return output

    def _getFieldsInString(self, inputString, document = None):
        document = document if document != None else self._document
        if document is None:
            # No document context to resolve fields, return as is
            return inputString

        if not isinstance(inputString, basestring):
            # Input is not a string, return the original input
            return inputString
        
        if '{' and '}' in inputString:
            # Inline fields detected
            fieldNames = [i.split('}')[0] for i in inputString.split('{')[1:]]
            for fieldName in fieldNames:
                if ':' in fieldName or ',' in fieldName:
                    # Not a fieldname, likely a dict
                    continue
                inputString = self._toUnicode(inputString).replace('{'+fieldName+'}', self._getField(fieldName, document) )
        return(inputString)

    def _getCallerInfo(self, depth=3):
        """
        Retrieves caller information using inspect module.
        """
        frame = inspect.currentframe()
        for _ in range(depth):
            frame = frame.f_back
            if frame is None:
                return ''
        
        code = frame.f_code

        # Get class name if available
        className = ''
        try:
            loc = frame.f_locals
            if 'self' in loc and loc['self'] is not None:
                className = loc['self'].__class__.__name__
        except Exception:
            pass

        if code.co_name == '<module>':
            return ''
        
        # Get parameters
        try:
            args, varargs, varkw, localsDict = inspect.getargvalues(frame)
            funcArgs = {}

            # Positional/named args: skip self instead of including it
            for name in args:
                if name == 'self':
                    continue
                funcArgs[name] = localsDict.get(name)

            # *args
            if varargs and varargs != 'self':
                funcArgs[varargs] = localsDict.get(varargs)

            # **kwargs
            if varkw and varkw != 'self':
                funcArgs[varkw] = localsDict.get(varkw)
        except Exception:
            funcArgs = {}
        argString = ', '.join('{}={}'.format(k, repr(v)) for k, v in funcArgs.items())

        lineNumber = frame.f_lineno
        funcName = code.co_name or ''

        if className:
            funcName = '{}.{}'.format(className, funcName)

        output = '\n{}() line={}:\n    params: {}'.format(funcName, lineNumber, argString)

        return output
    
    def _getMessageHeader(self, level, showCaller=True):
        levelAlias = self.LEVEL_MAP[level]['display']
        header = '\n[{}] {}'.format(levelAlias, self._label)     
        if showCaller:
            header += self._getCallerInfo()
        return header

    def _formatMessage(self, msg, label, messageList, multiple=False):
        """
        Formats a message and label and appends it to the message list.
        If msg is a string, it combines the label and message.
        Otherwise, it appends the label (if any) and the message separately.
        """        
        if multiple:
            # Treat iterable elements as separate messages using new lines
            multipleList = []
            try:
                if isinstance(msg, dict):
                    for key, value in msg.items():
                        self._formatMessage(value, key, multipleList)
                else:
                    for index, value in enumerate(msg):
                        self._formatMessage(value, str(index), multipleList)
            except Exception as e:
                messageList.append('Format error: {}'.format(str(e)))

            if multipleList:
                msg = '\n    ' + '\n    '.join(multipleList)
                
        if not label:
            label = 'msg'
        messageList.append('    {}: {}'.format(label, msg))

    def log(self, msg, label=None, multiple = False, enabled=False, document=None, level='debug', showCaller=True):
        if self._shouldLog(level) or enabled:
            output = []
            header = self._getMessageHeader(level=level, showCaller=showCaller)

            self._formatMessage(msg, label, output, multiple=multiple)

            for line in output:
                Rutilities.debug(self._getFieldsInString(header + '\n' + line, document=document))
    
    def alert(self, msg, label=None, multiple = False, document=None, level='debug', enabled=False):
        if self._shouldLog(level) or enabled:
            output = []
            self._formatMessage(msg, label, output, multiple=multiple)

            for line in output:
                document.addWarning(line)  

    def databaseTableInfo(self, tableName, schemaName='dbo', includeRowCount=True, filterOnlyDataSource='FILTER_ONLY', filterName='VAR$FILTER'):
        """
        Fetch comprehensive metadata for a table from INFORMATION_SCHEMA.
        Returns: dict with 'columns', 'indexes', 'constraints', 'rowCount', 'tableName'
        Note: Optimized for MySQL; adjust for SQL Server if needed.
        ETQ auto-prefixes table names with environment UUID, so pass the logical table name.
        """
        try:
            info = {
                'tableName': tableName,
                'schema': schemaName,
                'columns': [],
                'indexes': [],
                'constraints': [],
                'rowCount': None
            }
            
            # Fetch columns (MySQL INFORMATION_SCHEMA)
            columnsQuery = '\n'.join([
                "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_KEY",
                "FROM INFORMATION_SCHEMA.COLUMNS",
                "WHERE TABLE_NAME = '{}'".format(tableName),
                "  AND TABLE_SCHEMA NOT IN ('information_schema', 'mysql', 'performance_schema') AND TABLE_SCHEMA = '{}'".format(schemaName),
                "ORDER BY ORDINAL_POSITION"
            ])
            
            dao = thisApplication.executeQueryFromDatasource(filterOnlyDataSource, {filterName: columnsQuery})
            while dao.next():
                info['columns'].append({
                    'name': dao.getValue('COLUMN_NAME'),
                    'type': dao.getValue('DATA_TYPE'),
                    'maxLength': dao.getValue('CHARACTER_MAXIMUM_LENGTH') or 'N/A',
                    'nullable': dao.getValue('IS_NULLABLE'),
                    'key': dao.getValue('COLUMN_KEY') or ''
                })
        
            # Fetch indexes (MySQL)
            indexesQuery = '\n'.join([
                "SELECT INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX",
                "FROM INFORMATION_SCHEMA.STATISTICS",
                "WHERE TABLE_NAME = '{}'".format(tableName),
                "  AND TABLE_SCHEMA NOT IN ('information_schema', 'mysql', 'performance_schema') AND TABLE_SCHEMA = '{}'".format(schemaName),
                "ORDER BY INDEX_NAME, SEQ_IN_INDEX"
            ])
            
            dao = thisApplication.executeQueryFromDatasource(filterOnlyDataSource, {filterName: indexesQuery})
            currentIndex = None
            while dao.next():
                idxName = dao.getValue('INDEX_NAME')
                if idxName != currentIndex:
                    currentIndex = idxName
                    info['indexes'].append({'name': idxName, 'columns': []})
                if info['indexes']:
                    info['indexes'][-1]['columns'].append(dao.getValue('COLUMN_NAME'))
        
            # Fetch row count (optional, can be slow on large tables)
            if includeRowCount:
                countQuery = '\n'.join([
                    "SELECT TABLE_ROWS AS rowCount",
                    "FROM INFORMATION_SCHEMA.TABLES",
                    "WHERE TABLE_NAME = '{}'".format(tableName),
                    "  AND TABLE_SCHEMA NOT IN ('information_schema', 'mysql', 'performance_schema') AND TABLE_SCHEMA = '{}'".format(schemaName)
                ])
                dao = thisApplication.executeQueryFromDatasource(filterOnlyDataSource, {filterName: countQuery})
                if dao.next():
                    info['rowCount'] = dao.getValue('rowCount')
        
            self.log(info, "Database table info: {}.{}".format(schemaName, tableName), multiple=True, enabled=True)
            return info
    
        except Exception as e:
            self.log("Failed to fetch info for {}.{}: {}".format(schemaName, tableName, str(e)), label="databaseTableInfo", enabled=True)
            return {}
        
    def profileCode(self, codeOrFunc, *args, **kwargs):
        """
        Profiles either a function/method (using runcall) or a string of code (using runctx).
        Logs the results using the EtqDebug logger.
        
        Args:
            codeOrFunc (str or callable): The code string or function/method to profile.
            *args: Arguments for the function (if profiling a function).
            globals (dict, optional): Pass globals() from the calling scope (if profiling a string).
            locals (dict, optional): Pass locals() from the calling scope (if profiling a string).
            **kwargs: Keyword arguments for the function (if profiling a function).
        """        
        isString = isinstance(codeOrFunc, str)
        isFunction = not isString and callable(codeOrFunc)
        
        if not (isString or isFunction):
            self.log('codeOrFunc must be either a string or a callable', 'profileCode()')
            return
        
        logLabelPrefix = "ProfilerString" if isString else "ProfilerFunction"
        logLabel = "{prefix} -> {name}".format(prefix=logLabelPrefix, name='codeBlock' if isString else getattr(codeOrFunc, '__name__', 'codeBlock'))

        # Check if globals/locals were passed in kwargs
        # We must capture these *before* we potentially execute the code below
        scopeGlobals = kwargs.pop('globals', {})
        scopeLocals = kwargs.pop('locals', {})


        if not self._shouldLog('debug'):
            if isString:
                # Execute normally if profiling is disabled
                exec(codeOrFunc, scopeGlobals, scopeLocals)
                return
            else:
                return codeOrFunc(*args, **kwargs)

        # --- Imports needed ONLY if we are allowed to log ---    
        from StringIO import StringIO 
        import profile
        import pstats

        self.log("Starting profile run for: {logLabel}".format(logLabel=logLabel), 'Starting profile')
        pr = profile.Profile()
        result = None
        
        try:
            if isString:
                # Handle as a string using runctx() with provided scopes
                pr.runctx(codeOrFunc, scopeGlobals, scopeLocals)
            else:
                # Handle as a function using runcall()
                result = pr.runcall(codeOrFunc, *args, **kwargs)
                
        except Exception as e:
            self.log("Error during profiled execution: {e}".format(e=str(e)), "ProfilerError")
            raise

        # --- Stats Capture (shared logic) ---
        s = StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        profileStatsString = s.getvalue()
        statsLines = profileStatsString.strip().split('\n')
        self.log('\n' + '\n'.join(statsLines), logLabel + " - Profile Results:")
        
        return result
    
    def profileThis(self, func):
        """
        A decorator that profiles a function execution and logs the results 
        using the EtqDebug logger and the internal profileCode method.
        """        
        import functools
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # This calls the existing profileCode method using 'self' (the debug instance)
            return self.profileCode(func, *args, **kwargs)
            
        return wrapper
