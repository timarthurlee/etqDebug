class EtqDebug(object):
    def __init__(self, label=None, enabled=True, mode='info', force=False, document=None):      
        modes = ['debug', 'info', 'warning', 'error']  
        env = engineConfig.getEnvironmentName()
        isProd = env == 'Production'
        self._document = document
        self._force = force
        self._enabled = enabled and (not isProd or thisUser.isMember('ADMINISTRATORS',None) or force)
        self._label = self._getFieldsInString(label) or "EtqDebug"

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
        if field != None:
            fieldSetting = field.getSetting()
            if fieldSetting.getFieldType() in [fieldSetting.FIELD_TYPE_LINK]:
                links = field.getDocLinks()
                if links:
                   output = separator.join(links.getDescription(field.getLocale(), thisUser.getTimeZone()))
            elif fieldSetting.getFieldType() not in [fieldSetting.FIELD_TYPE_ATTACHMENT]:
                #if fieldSetting.isMultiValue():
                #    output = separator.join(field.getEncodedTextList())
                #else:
                output = field.getEncodedDisplayText()
        else:
            self.log('Invalid fieldname provided.', 'getField:')

        return output

    def _getFieldsInString(self, inputString, document = None):
        document = document if document != None else self._document
        if document is None:
            # No document context to resolve fields, return as is
            return inputString

        if not isinstance(inputString, str):
            # Input is not a string, return the original input
            return inputString
        
        if '{' and '}' in inputString:
            # Inline fields detected
            fieldNames = [i.split('}')[0] for i in inputString.split('{')[1:]]
            for fieldName in fieldNames:              
                inputString = self._toUnicode(inputString).replace('{'+fieldName+'}', self._getField(fieldName, document) )
        return(inputString)
            
    def log(self, msg, label=None, multiple = False, enabled=False):
        if self._enabled or enabled or self._force:
            output = []
            if label:
                label = '{} :: {}'.format(self._label, label)
            else:
                label = self._label

            if multiple and (isinstance(msg, list) or isinstance(msg, dict)):
                if label:
                    output = ['--{}--'.format(label)]

                if label and isinstance(msg, dict):
                    output.extend([item for key, value in msg.items() for item in [key + ':', value]])
                        
                if label and isinstance(msg, list):
                    # output.extend([item for index, value in enumerate(msg) for item in [label + ' - ' + str(index) + ':', value]])      
                    output.extend([item for index, value in enumerate(msg) for item in ['{} - {}:{}'.format(label,str(index),value)]])      
                          
            else:
                output = [msg]
                if label and isinstance(msg, str):
                    output = [label + ': ' + msg]
                else:
                    output = [label, msg]

            for line in output:
                Rutilities.debug(self._getFieldsInString(line))
    
    def alert(self, msg, label=None, multiple = False, document=None, enabled=False):
        if (self._enabled or enabled or self._force) and document is not None:
            output = []
            if label:
                label = '{} :: {}'.format(self._label, label)
            else:
                label = self._label

            if multiple and (isinstance(msg, list) or isinstance(msg, dict)):
                if label:
                    output = ['--{}--'.format(label)]

                if label and isinstance(msg, dict):
                    output.extend([item for key, value in msg.items() for item in [key + ':', value]])
                        
                if label and isinstance(msg, list):
                    # output.extend([item for index, value in enumerate(msg) for item in [label + ' - ' + str(index) + ':', value]])      
                    output.extend([item for index, value in enumerate(msg) for item in ['{} - {}:{}'.format(label,str(index),value)]])      
                          
            else:
                output = [label + ': ' + str(msg)]

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
