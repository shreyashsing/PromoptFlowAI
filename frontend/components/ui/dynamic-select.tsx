'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Loader2, RefreshCw, Search, AlertCircle, CheckCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/lib/auth-context';

interface FieldOption {
  value: string;
  label: string;
  description?: string;
  metadata?: Record<string, any>;
}

interface DynamicSelectProps {
  connectorName: string;
  fieldName: string;
  value?: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  context?: Record<string, any>;
  disabled?: boolean;
  className?: string;
  searchable?: boolean;
  showRefresh?: boolean;
  skipInitialFetch?: boolean; // Skip fetching on mount if we already have a value
  cacheKey?: string; // Custom cache key for better caching
}

// Simple cache for options to prevent unnecessary refetches
const optionsCache = new Map<string, { options: FieldOption[], timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export function DynamicSelect({
  connectorName,
  fieldName,
  value,
  onValueChange,
  placeholder,
  context,
  disabled = false,
  className,
  searchable = false,
  showRefresh = true,
  skipInitialFetch = false,
  cacheKey
}: DynamicSelectProps) {
  const { session } = useAuth();
  const [options, setOptions] = useState<FieldOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);

  const fetchOptions = useCallback(async (searchTerm?: string, forceRefresh = false) => {
    if (!session?.access_token) {
      setError('Authentication required');
      return;
    }

    // Create cache key
    const contextKey = JSON.stringify({ ...context, ...(searchTerm && { query: searchTerm }) });
    const fullCacheKey = cacheKey || `${connectorName}-${fieldName}-${contextKey}`;
    
    // Check cache first (unless forcing refresh or searching)
    if (!forceRefresh && !searchTerm) {
      const cached = optionsCache.get(fullCacheKey);
      if (cached && (Date.now() - cached.timestamp) < CACHE_DURATION) {
        console.log('🔄 DynamicSelect: Using cached options for', { connectorName, fieldName });
        setOptions(cached.options);
        setError(null);
        setHasFetched(true);
        return;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const requestBody = {
        connector_name: connectorName,
        field_name: fieldName,
        context: {
          ...context,
          ...(searchTerm && { query: searchTerm })
        }
      };

      console.log('🔄 DynamicSelect: Fetching options for', { connectorName, fieldName, context: requestBody.context });

      const response = await fetch(`${baseUrl}/api/v1/connector-fields/fetch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('✅ DynamicSelect: Received options', data);

      if (data.success) {
        const fetchedOptions = data.options || [];
        setOptions(fetchedOptions);
        setError(null);
        setHasFetched(true);
        
        // Cache the results (but not search results)
        if (!searchTerm) {
          optionsCache.set(fullCacheKey, {
            options: fetchedOptions,
            timestamp: Date.now()
          });
        }
      } else {
        setError(data.error || 'Failed to fetch options');
        setOptions([]);
      }
    } catch (err) {
      console.error('❌ DynamicSelect: Error fetching options:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch options');
      setOptions([]);
    } finally {
      setLoading(false);
    }
  }, [connectorName, fieldName, context, session?.access_token, cacheKey]);

  // Initial fetch when component mounts or dependencies change
  useEffect(() => {
    // Skip initial fetch if we have a value and skipInitialFetch is true
    if (skipInitialFetch && value && !hasFetched) {
      return;
    }
    
    // Only fetch if we haven't fetched yet or if dependencies changed
    if (!hasFetched || !skipInitialFetch) {
      fetchOptions();
    }
  }, [fetchOptions, skipInitialFetch, value, hasFetched]);

  // Handle search with debouncing
  useEffect(() => {
    if (!searchable) return;

    const timeoutId = setTimeout(() => {
      if (searchQuery.trim()) {
        fetchOptions(searchQuery.trim());
      } else {
        fetchOptions();
      }
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [searchQuery, fetchOptions, searchable]);

  const handleRefresh = () => {
    fetchOptions(searchable && searchQuery ? searchQuery : undefined, true); // Force refresh
  };

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    // Only fetch when opening if we have no options and haven't fetched yet
    if (open && options.length === 0 && !loading && !error && !hasFetched) {
      fetchOptions();
    }
  };

  const filteredOptions = searchable && searchQuery
    ? options.filter(option =>
      option.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      option.value.toLowerCase().includes(searchQuery.toLowerCase())
    )
    : options;

  const selectedOption = options.find(opt => opt.value === value);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <Select
            value={value}
            onValueChange={onValueChange}
            disabled={disabled || loading}
            onOpenChange={handleOpenChange}
            open={isOpen}
          >
            <SelectTrigger className={className}>
              <SelectValue placeholder={loading ? "Loading..." : placeholder}>
                {selectedOption ? (
                  <div className="flex items-center gap-2">
                    <span className="truncate">{selectedOption.label}</span>
                    {selectedOption.description && (
                      <Badge variant="outline" className="text-xs">
                        {selectedOption.description}
                      </Badge>
                    )}
                  </div>
                ) : (
                  placeholder
                )}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {searchable && (
                <div className="p-2 border-b">
                  <div className="relative">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
                    <Input
                      placeholder="Search..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8"
                    />
                  </div>
                </div>
              )}

              {loading && (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  <span className="text-sm text-gray-500">Loading options...</span>
                </div>
              )}

              {error && (
                <div className="p-2">
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-xs">{error}</AlertDescription>
                  </Alert>
                </div>
              )}

              {!loading && !error && filteredOptions.length === 0 && (
                <div className="p-4 text-center text-sm text-gray-500">
                  No options available
                </div>
              )}

              {!loading && !error && filteredOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  <div className="flex flex-col items-start">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{option.label}</span>
                      {option.metadata?.type && (
                        <Badge variant="outline" className="text-xs">
                          {option.metadata.type}
                        </Badge>
                      )}
                    </div>
                    {option.description && (
                      <span className="text-xs text-gray-500 mt-1">
                        {option.description}
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {showRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
            className="px-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        )}
      </div>

      {/* Status indicator */}
      <div className="flex items-center gap-2 text-xs">
        {loading && (
          <div className="flex items-center gap-1 text-blue-600">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Fetching real-time data...</span>
          </div>
        )}

        {!loading && !error && options.length > 0 && (
          <div className="flex items-center gap-1 text-green-600">
            <CheckCircle className="h-3 w-3" />
            <span>{options.length} options loaded from your account</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-1 text-red-600">
            <AlertCircle className="h-3 w-3" />
            <span>Failed to load account data</span>
          </div>
        )}
      </div>
    </div>
  );
}